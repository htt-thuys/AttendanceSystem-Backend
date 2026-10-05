from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

from infrastructure.database.models import Employee, Meeting
from modules.events import service as events_service
from modules.meetings import service as meetings_service
from modules.recognition.orchestrator import process_recognition
from modules.recognition.schemas import RecognizeResponse


async def recognize_face(
    db: AsyncSession,
    image_bytes: bytes,
    camera_id: int | str | None,
    meeting_id: int | str | None = None,
    event_id: int | str | None = None,
    filename: str = "image.jpg",
    content_type: str = "image/jpeg",
) -> RecognizeResponse:
    normalized_camera_id = _normalize_camera_id(camera_id)
    normalized_meeting_id = _normalize_meeting_id(meeting_id)
    normalized_event_id = _normalize_event_id(event_id)
    if normalized_meeting_id is not None:
        await meetings_service.ensure_recognition_meeting_context(
            db=db,
            meeting_id=normalized_meeting_id,
            camera_id=normalized_camera_id,
        )

    captured_at = datetime.now(tz=timezone.utc)
    active_event = await events_service.resolve_active_event_for_recognition(
        db=db,
        event_id=normalized_event_id,
        captured_at=captured_at,
    )
    active_event_id = active_event.id if active_event else None

    result = await process_recognition(
        db=db,
        image_bytes=image_bytes,
        camera_id=normalized_camera_id,
        event_id=active_event_id,
        meeting_id=normalized_meeting_id,
        filename=filename,
        content_type=content_type,
    )

    if result["label"] == "no_face":
        return RecognizeResponse(
            label="no_face",
            event_id=active_event_id,
            event=_build_event_basic(active_event),
            meeting_id=normalized_meeting_id,
            meeting=await _build_meeting_basic(db, normalized_meeting_id),
            log_saved=False,
        )

    if result["label"] == "spoof_detected":
        return RecognizeResponse(
            label="spoof_detected",
            event_id=active_event_id,
            event=_build_event_basic(active_event),
            meeting_id=normalized_meeting_id,
            meeting=await _build_meeting_basic(db, normalized_meeting_id),
            log_saved=False,
            live_score=result.get("live_score"),
            spoof_score=result.get("spoof_score"),
        )

    await db.commit()

    emp_id = result.get("employee_id")
    employee_info = None
    auto_attendance = None
    auto_meeting_checkin = None

    if emp_id:
        query = select(Employee).where(
            Employee.id == int(emp_id),
            Employee.status != "deleted",
        )
        emp_result = await db.execute(query)
        emp_db = emp_result.scalar_one_or_none()
        if emp_db:
            employee_info = {
                "id": emp_db.id,
                "full_name": emp_db.full_name,
            }

    return RecognizeResponse(
        label=result["label"],
        recognition_log_id=result.get("recognition_log_id"),
        employee=employee_info,
        score=result.get("score"),
        candidates=result.get("candidates"),
        auto_attendance=auto_attendance,
        auto_meeting_checkin=auto_meeting_checkin,
        event_id=active_event_id,
        event=_build_event_basic(active_event),
        meeting_id=normalized_meeting_id,
        meeting=await _build_meeting_basic(db, normalized_meeting_id),
        log_saved=result.get("log_saved"),
    )


def _normalize_camera_id(camera_id: int | str | None) -> int | None:
    if camera_id in (None, ""):
        return None
    try:
        return int(camera_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="camera_id khong hop le") from exc


def _normalize_meeting_id(meeting_id: int | str | None) -> int | None:
    if meeting_id in (None, ""):
        return None
    try:
        return int(meeting_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="meeting_id khong hop le") from exc


def _normalize_event_id(event_id: int | str | None) -> int | None:
    if event_id in (None, ""):
        return None
    try:
        return int(event_id)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="event_id khong hop le") from exc


def _build_event_basic(event) -> dict | None:
    if event is None:
        return None
    return {
        "id": event.id,
        "title": event.title,
    }


async def _build_meeting_basic(db: AsyncSession, meeting_id: int | None) -> dict | None:
    if meeting_id is None:
        return None
    meeting_result = await db.execute(
        select(Meeting).where(Meeting.id == meeting_id)
    )
    meeting = meeting_result.scalar_one_or_none()
    if meeting is None:
        return None
    return {
        "id": meeting.id,
        "title": meeting.title,
    }
