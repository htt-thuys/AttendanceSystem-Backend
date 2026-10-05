from datetime import date, datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Event, User
from infrastructure.settings.runtime_settings import get_runtime_settings
from modules.events import repository
from modules.events.schemas import (
    EventAttendanceLogResponse,
    EventAttendanceResponse,
    EventBasicResponse,
    EventCreateRequest,
    EventResponse,
    EventUpdateRequest,
)
from storage.image_store import build_image_url


async def create_event(
    db: AsyncSession,
    payload: EventCreateRequest,
    current_user: User,
) -> EventResponse:
    _validate_event_window(payload.starts_at, payload.ends_at)
    event = await repository.create_event_record(
        db=db,
        title=payload.title,
        description=payload.description,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        created_by=current_user.id,
    )
    await db.commit()
    await db.refresh(event)
    return _build_event_response(event)


async def list_events(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[EventResponse]:
    if status is not None and status not in {"active", "inactive", "running", "upcoming", "ended", "all"}:
        raise HTTPException(status_code=400, detail="status khong hop le")

    rows = await repository.list_event_records(
        db=db,
        date_from=date_from,
        date_to=date_to,
        status=status,
        limit=limit,
        offset=offset,
        now=datetime.now(tz=timezone.utc),
    )
    return [_build_event_response(event) for event in rows]


async def list_active_public_events(
    db: AsyncSession,
    limit: int | None = None,
) -> list[EventBasicResponse]:
    runtime_settings = await get_runtime_settings(db)
    rows = await repository.list_upcoming_public_event_records(
        db=db,
        now=datetime.now(tz=timezone.utc),
        lookahead_minutes=runtime_settings.event_tablet_lookahead_minutes,
        limit=limit,
    )
    return [_build_event_basic_response(event) for event in rows]


async def list_upcoming_public_events(
    db: AsyncSession,
    limit: int | None = None,
) -> list[EventBasicResponse]:
    return await list_active_public_events(db=db, limit=limit)


async def get_event_detail(db: AsyncSession, event_id: int) -> EventResponse:
    event = await _get_event_or_404(db=db, event_id=event_id)
    return _build_event_response(event)


async def get_event_attendance(db: AsyncSession, event_id: int) -> EventAttendanceResponse:
    event = await _get_event_or_404(db=db, event_id=event_id)
    rows = await repository.list_event_attendance_logs(db=db, event_id=event_id)

    attendees: list[EventAttendanceLogResponse] = []
    present_employee_ids: set[int] = set()
    status_counts = {
        "present": 0,
        "pending": 0,
        "unknown": 0,
        "rejected": 0,
    }

    for log_entry, employee_name, employee_code in rows:
        status = _derive_event_attendance_status(log_entry)
        status_counts[status] += 1
        if status == "present" and log_entry.employee_id is not None:
            present_employee_ids.add(log_entry.employee_id)
        attendees.append(
            EventAttendanceLogResponse(
                id=log_entry.id,
                employee_id=log_entry.employee_id,
                employee_name=employee_name,
                employee_code=employee_code,
                check_in_time=log_entry.captured_at,
                status=status,
                result_label=log_entry.result_label,
                final_label=log_entry.final_label,
                top_score=log_entry.top_score,
                face_image_path=log_entry.face_image_path,
                face_image_url=build_image_url(log_entry.face_image_path),
            )
        )

    return EventAttendanceResponse(
        event_id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        is_active=event.is_active,
        total_logs=len(attendees),
        total_recognized_employees=len(present_employee_ids),
        present_count=status_counts["present"],
        pending_count=status_counts["pending"],
        unknown_count=status_counts["unknown"],
        rejected_count=status_counts["rejected"],
        attendees=attendees,
    )


async def update_event(
    db: AsyncSession,
    event_id: int,
    payload: EventUpdateRequest,
) -> EventResponse:
    event = await _get_event_or_404(db=db, event_id=event_id)

    if payload.title is not None:
        event.title = payload.title
    if payload.description is not None:
        event.description = payload.description
    if payload.starts_at is not None:
        event.starts_at = payload.starts_at
    if payload.ends_at is not None:
        event.ends_at = payload.ends_at
    if payload.is_active is not None:
        event.is_active = payload.is_active

    _validate_event_window(event.starts_at, event.ends_at)
    await db.commit()
    await db.refresh(event)
    return _build_event_response(event)


async def deactivate_event(db: AsyncSession, event_id: int) -> EventResponse:
    event = await _get_event_or_404(db=db, event_id=event_id)
    event.is_active = False
    await db.commit()
    await db.refresh(event)
    return _build_event_response(event)


async def resolve_active_event_for_recognition(
    db: AsyncSession,
    event_id: int | None,
    captured_at: datetime | None = None,
) -> Event | None:
    if event_id is None:
        return None

    event = await _get_event_or_404(db=db, event_id=event_id)
    captured_at = _as_aware_utc(captured_at or datetime.now(tz=timezone.utc))
    if not event.is_active:
        return None
    if captured_at > _as_aware_utc(event.ends_at):
        return None
    return event


async def _get_event_or_404(db: AsyncSession, event_id: int) -> Event:
    event = await repository.get_event_record(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Khong tim thay event")
    return event


def _validate_event_window(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at <= starts_at:
        raise HTTPException(status_code=400, detail="Thoi gian ket thuc event phai sau thoi gian bat dau")


def _build_event_response(event: Event) -> EventResponse:
    return EventResponse(
        id=event.id,
        title=event.title,
        description=event.description,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
        is_active=event.is_active,
        created_by=event.created_by,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


def _build_event_basic_response(event: Event) -> EventBasicResponse:
    return EventBasicResponse(
        id=event.id,
        title=event.title,
        starts_at=event.starts_at,
        ends_at=event.ends_at,
    )


def _derive_event_attendance_status(log_entry) -> str:
    if log_entry.final_label == "confirmed":
        return "present"
    if log_entry.result_label == "unknown":
        return "unknown"
    if log_entry.final_label == "rejected":
        return "rejected"
    return "pending"


def _as_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
