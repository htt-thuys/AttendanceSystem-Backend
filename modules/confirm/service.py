import logging
from datetime import datetime, timedelta, timezone

import numpy as np
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import FaceVector, RecognitionLog, UnknownQueue
from infrastructure.settings.runtime_settings import get_runtime_settings
from infrastructure.vector_db.qdrant_client import upsert_vector
from modules.attendance import service as attendance_service
from modules.confirm.schemas import ConfirmRequest, ConfirmResponse
from modules.events import service as events_service
from modules.meetings import service as meetings_service
from modules.recognition.runtime_store import temp_vectors
from storage.image_store import copy_to_unknown_queue, copy_to_vector_source

logger = logging.getLogger(__name__)

VALID_CONFIRM_ACTIONS = {
    "sure_ok",
    "sure_wrong_choose",
    "sure_wrong_no_match",
    "review_correct",
    "review_choose",
    "review_no_match",
}

CONFIRM_ACTIONS_BY_LABEL = {
    "sure": {"sure_ok", "sure_wrong_choose", "sure_wrong_no_match"},
    "review": {"review_correct", "review_choose", "review_no_match"},
    "unknown": {"review_no_match"},
}


async def confirm_recognition(
    db: AsyncSession,
    req: ConfirmRequest,
) -> ConfirmResponse:
    if req.action not in VALID_CONFIRM_ACTIONS:
        raise HTTPException(status_code=400, detail="Action khong hop le")

    query = select(RecognitionLog).where(RecognitionLog.id == req.recognition_log_id)
    result = await db.execute(query)
    log_entry = result.scalar_one_or_none()

    if not log_entry:
        raise HTTPException(status_code=404, detail="Khong tim thay recognition_log_id")

    allowed_actions = CONFIRM_ACTIONS_BY_LABEL.get(log_entry.result_label, set())
    if req.action not in allowed_actions:
        raise HTTPException(status_code=400, detail="Action khong phu hop voi recognition label")

    if log_entry.resolved_at is not None:
        return ConfirmResponse(success=True, message="log da duoc xu ly")

    temp_entry = temp_vectors.get(req.recognition_log_id)
    vector = temp_entry["vector"] if temp_entry else None
    face_quality = temp_entry["face_quality"] if temp_entry else None

    target_meeting_id = req.meeting_id if req.meeting_id is not None else log_entry.meeting_id
    target_event_id = await _resolve_confirm_event_id(
        db=db,
        event_id=req.event_id,
        fallback_event_id=log_entry.event_id,
        captured_at=log_entry.captured_at,
    )
    log_entry.meeting_id = target_meeting_id
    log_entry.event_id = target_event_id
    log_entry.resolved_at = func.now()
    confirmed_employee_id: int | None = None
    duplicate_message: str | None = None

    if req.action == "sure_ok":
        confirmed_employee_id, duplicate_message = await _confirm_employee_if_not_duplicate(
            db=db,
            log_entry=log_entry,
            employee_id=log_entry.employee_id,
            vector=vector,
            face_quality=face_quality,
            source="auto_sure",
        )

    elif req.action == "sure_wrong_choose":
        if not req.employee_id:
            raise HTTPException(status_code=400, detail="action='sure_wrong_choose' yeu cau employee_id")
        confirmed_employee_id, duplicate_message = await _confirm_employee_if_not_duplicate(
            db=db,
            log_entry=log_entry,
            employee_id=req.employee_id,
            vector=vector,
            face_quality=face_quality,
            source="manual",
        )

    elif req.action == "sure_wrong_no_match":
        log_entry.final_label = "rejected"
        log_entry.employee_id = None
        if vector:
            await _upsert_unknown_queue_from_log(
                db=db,
                log_entry=log_entry,
                vector=vector,
                face_quality=face_quality,
            )

    elif req.action == "review_correct":
        confirmed_employee_id, duplicate_message = await _confirm_employee_if_not_duplicate(
            db=db,
            log_entry=log_entry,
            employee_id=log_entry.employee_id,
            vector=vector,
            face_quality=face_quality,
            source="auto_reviewed",
        )

    elif req.action == "review_choose":
        if not req.employee_id:
            raise HTTPException(status_code=400, detail="action='review_choose' yeu cau employee_id")
        confirmed_employee_id, duplicate_message = await _confirm_employee_if_not_duplicate(
            db=db,
            log_entry=log_entry,
            employee_id=req.employee_id,
            vector=vector,
            face_quality=face_quality,
            source="manual",
        )

    elif req.action == "review_no_match":
        log_entry.final_label = "rejected"
        log_entry.employee_id = None
        if vector:
            await _upsert_unknown_queue_from_log(
                db=db,
                log_entry=log_entry,
                vector=vector,
                face_quality=face_quality,
            )

    else:
        raise HTTPException(status_code=400, detail="Action khong hop le")

    if confirmed_employee_id:
        try:
            await attendance_service.record_auto_attendance(
                db=db,
                employee_id=confirmed_employee_id,
                recognition_log_id=log_entry.id,
                captured_at=log_entry.captured_at,
            )
        except Exception:
            logger.warning("Confirmed attendance sync failed for employee %s", confirmed_employee_id, exc_info=True)

        if target_meeting_id is not None:
            try:
                await meetings_service.auto_checkin_selected_meeting(
                    db=db,
                    meeting_id=target_meeting_id,
                    employee_id=confirmed_employee_id,
                    recognition_log_id=log_entry.id,
                    captured_at=log_entry.captured_at,
                    camera_id=log_entry.camera_id,
                )
            except HTTPException:
                raise
            except Exception:
                logger.warning(
                    "Confirmed meeting check-in failed for employee %s, meeting %s",
                    confirmed_employee_id,
                    target_meeting_id,
                    exc_info=True,
                )

    await db.commit()

    if req.recognition_log_id in temp_vectors:
        del temp_vectors[req.recognition_log_id]

    return ConfirmResponse(success=True, message=duplicate_message)


async def _resolve_confirm_event_id(
    db: AsyncSession,
    event_id: int | None,
    fallback_event_id: int | None,
    captured_at,
) -> int | None:
    if event_id is None:
        return fallback_event_id

    event = await events_service.resolve_active_event_for_recognition(
        db=db,
        event_id=event_id,
        captured_at=captured_at,
    )
    if event is None:
        raise HTTPException(status_code=400, detail="event_id khong hop le hoac event da ket thuc")
    return event.id


async def _upsert_unknown_queue_from_log(
    db: AsyncSession,
    log_entry: RecognitionLog,
    vector: list[float],
    face_quality: float | None,
) -> None:
    if not log_entry.face_image_path:
        raise HTTPException(status_code=400, detail="Thieu anh nguon de dua vao unknown_queue")

    runtime_settings = await get_runtime_settings(db)
    result = await db.execute(
        select(UnknownQueue).where(
            UnknownQueue.resolved_at.is_(None),
            UnknownQueue.event_id == log_entry.event_id,
            UnknownQueue.meeting_id == log_entry.meeting_id,
        )
    )
    unresolved_list = result.scalars().all()

    best_match = None
    best_sim = -1.0
    for unknown_item in unresolved_list:
        sim = _cosine_similarity(vector, unknown_item.vector)
        if sim > best_sim:
            best_sim = sim
            best_match = unknown_item

    effective_face_quality = face_quality if face_quality is not None else 0.0
    if best_match and best_sim > runtime_settings.dedup_threshold:
        best_match.attempt_count += 1
        best_match.last_seen_at = func.now()
        if effective_face_quality > (best_match.face_quality or 0):
            best_match.camera_id = log_entry.camera_id
            best_match.image_path = await copy_to_unknown_queue(log_entry.face_image_path)
            best_match.vector = vector
            best_match.face_quality = effective_face_quality
        return

    db.add(
        UnknownQueue(
            camera_id=log_entry.camera_id,
            event_id=log_entry.event_id,
            meeting_id=log_entry.meeting_id,
            image_path=await copy_to_unknown_queue(log_entry.face_image_path),
            vector=vector,
            face_quality=effective_face_quality,
            attempt_count=1,
        )
    )


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    a = np.array(v1)
    b = np.array(v2)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def _confirm_employee_if_not_duplicate(
    db: AsyncSession,
    log_entry: RecognitionLog,
    employee_id: int | None,
    vector: list[float] | None,
    face_quality: float | None,
    source: str,
) -> tuple[int | None, str | None]:
    if not employee_id:
        raise HTTPException(status_code=400, detail="Khong co employee_id de confirm")

    log_entry.employee_id = employee_id
    duplicate_log_id = await _find_existing_confirmed_log_id(
        db=db,
        log_entry=log_entry,
        employee_id=employee_id,
    )
    if duplicate_log_id is not None:
        log_entry.final_label = "rejected"
        return None, "employee da co confirmed log trong cooldown/event, log hien tai khong duoc confirm duplicate"

    log_entry.final_label = "confirmed"
    if vector:
        await _handle_selective_upsert(
            db=db,
            emp_id=employee_id,
            vector=vector,
            source=source,
            score=log_entry.top_score,
            source_image_path=log_entry.face_image_path,
            quality_score=face_quality,
        )
    return employee_id, None


async def _find_existing_confirmed_log_id(
    db: AsyncSession,
    log_entry: RecognitionLog,
    employee_id: int,
) -> int | None:
    if log_entry.event_id is not None:
        result = await db.execute(
            select(RecognitionLog.id)
            .where(
                RecognitionLog.id != log_entry.id,
                RecognitionLog.event_id == log_entry.event_id,
                RecognitionLog.employee_id == employee_id,
                RecognitionLog.final_label == "confirmed",
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    if log_entry.meeting_id is not None:
        result = await db.execute(
            select(RecognitionLog.id)
            .where(
                RecognitionLog.id != log_entry.id,
                RecognitionLog.meeting_id == log_entry.meeting_id,
                RecognitionLog.employee_id == employee_id,
                RecognitionLog.final_label == "confirmed",
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    runtime_settings = await get_runtime_settings(db)
    if runtime_settings.recognition_log_cooldown_minutes <= 0:
        return None

    captured_at = log_entry.captured_at or datetime.now(timezone.utc)
    cutoff = captured_at - timedelta(minutes=runtime_settings.recognition_log_cooldown_minutes)
    query = (
        select(RecognitionLog.id)
        .where(
            RecognitionLog.id != log_entry.id,
            RecognitionLog.employee_id == employee_id,
            RecognitionLog.final_label == "confirmed",
            RecognitionLog.captured_at >= cutoff,
            RecognitionLog.captured_at <= captured_at,
        )
        .order_by(RecognitionLog.captured_at.desc(), RecognitionLog.id.desc())
        .limit(1)
    )
    if log_entry.camera_id is None:
        query = query.where(RecognitionLog.camera_id.is_(None))
    else:
        query = query.where(RecognitionLog.camera_id == log_entry.camera_id)

    result = await db.execute(query)
    return result.scalar_one_or_none()


async def _handle_selective_upsert(
    db: AsyncSession,
    emp_id: int,
    vector: list[float],
    source: str,
    score: float,
    source_image_path: str | None,
    quality_score: float | None,
) -> None:
    runtime_settings = await get_runtime_settings(db)
    count_query = select(func.count()).where(FaceVector.employee_id == emp_id, FaceVector.is_active == True)
    count_result = await db.execute(count_query)
    vec_count = count_result.scalar()

    if (score and score < runtime_settings.upsert_score_max) or (
        vec_count < runtime_settings.upsert_min_vecs
    ):
        if not source_image_path:
            raise HTTPException(status_code=400, detail="Thieu anh nguon de tao vector moi")

        vector_source_path = await copy_to_vector_source(source_image_path)
        new_vec = FaceVector(
            employee_id=emp_id,
            qdrant_point_id=0,
            source=source,
            source_image_path=vector_source_path,
            quality_score=quality_score,
            score_at_create=score,
            is_active=True,
        )
        db.add(new_vec)
        await db.flush()

        new_vec.qdrant_point_id = new_vec.id

        payload = {
            "employee_id": emp_id,
            "face_vec_id": new_vec.id,
            "is_active": True,
        }
        upsert_vector(new_vec.id, vector, payload)
