from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import RecognitionLog
from modules.recognition.log_cooldown import find_recent_employee_log
from modules.recognition.runtime_store import temp_vectors
from storage.image_store import save_recognition_log_image


async def handle(
    db: AsyncSession,
    top_candidate: dict[str, Any],
    vector: list[float],
    face_quality: float,
    image_bytes: bytes,
    camera_id: int | str | None,
    event_id: int | None = None,
    meeting_id: int | None = None,
    cooldown_minutes: int = 0,
) -> dict[str, Any]:
    emp_id = top_candidate["employee_id"]
    top_score = top_candidate["score"]

    if isinstance(camera_id, str):
        camera_id = int(camera_id)

    duplicate_log = await _find_duplicate_confirmed_log(
        db=db,
        employee_id=emp_id,
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        cooldown_minutes=cooldown_minutes,
    )
    if duplicate_log is not None:
        return {
            "label": "sure",
            "employee_id": emp_id,
            "score": top_score,
            "recognition_log_id": None,
            "face_image_path": None,
            "log_saved": False,
        }

    image_path = await save_recognition_log_image(image_bytes)

    log_entry = RecognitionLog(
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        face_image_path=image_path,
        result_label="sure",
        top_score=top_score,
        employee_id=emp_id,
    )
    db.add(log_entry)
    await db.flush()

    temp_vectors[log_entry.id] = {
        "vector": vector,
        "face_quality": face_quality,
    }

    return {
        "label": "sure",
        "employee_id": emp_id,
        "score": top_score,
        "recognition_log_id": log_entry.id,
        "face_image_path": image_path,
        "log_saved": True,
    }


async def _find_duplicate_confirmed_log(
    db: AsyncSession,
    employee_id: int,
    camera_id: int | None,
    event_id: int | None,
    meeting_id: int | None,
    cooldown_minutes: int,
) -> RecognitionLog | None:
    if event_id is not None:
        result = await db.execute(
            select(RecognitionLog)
            .where(
                RecognitionLog.event_id == event_id,
                RecognitionLog.employee_id == employee_id,
                RecognitionLog.final_label == "confirmed",
            )
            .order_by(RecognitionLog.captured_at.desc(), RecognitionLog.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    if meeting_id is not None:
        result = await db.execute(
            select(RecognitionLog)
            .where(
                RecognitionLog.meeting_id == meeting_id,
                RecognitionLog.employee_id == employee_id,
                RecognitionLog.final_label == "confirmed",
            )
            .order_by(RecognitionLog.captured_at.desc(), RecognitionLog.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    return await find_recent_employee_log(
        db=db,
        employee_id=employee_id,
        camera_id=camera_id,
        cooldown_minutes=cooldown_minutes,
    )
