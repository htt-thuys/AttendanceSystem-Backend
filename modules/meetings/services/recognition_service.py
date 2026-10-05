"""Recognition-driven meeting attendance flows."""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from modules.meetings import repository
from modules.meetings.enums import ParticipantStatus
from modules.meetings.helpers import (
    as_aware_utc,
    derive_meeting_attendance_status,
    ensure_meeting_allows_recognition_checkin,
    ensure_meeting_matches_camera,
)
from modules.meetings.services.attendance_service import auto_start_meeting
from modules.meetings.services.validators import get_meeting_or_404


async def ensure_recognition_meeting_context(
    db: AsyncSession,
    meeting_id: int,
    camera_id: int | None = None,
) -> None:
    """Kiem tra meeting hop le cho recognition flow."""
    meeting = await get_meeting_or_404(db, meeting_id)
    ensure_meeting_matches_camera(meeting, camera_id)
    ensure_meeting_allows_recognition_checkin(
        meeting,
        datetime.now(tz=timezone.utc),
    )


async def auto_checkin_by_camera(
    db: AsyncSession,
    camera_id: int,
    employee_id: int,
    recognition_log_id: int | None,
    captured_at: datetime | None = None,
) -> list[int]:
    """Tu dong check-in nhan vien vao cac meeting dang phu hop theo camera."""
    now = captured_at or datetime.now(tz=timezone.utc)
    meetings = await repository.list_active_meetings_by_camera(
        db=db,
        camera_id=camera_id,
        captured_at=now,
    )
    checked_in: list[int] = []

    for meeting in meetings:
        result = await try_auto_checkin(
            db=db,
            meeting=meeting,
            employee_id=employee_id,
            captured_at=now,
            recognition_log_id=recognition_log_id,
        )
        if result is not None:
            checked_in.append(result)

    return checked_in


async def auto_checkin_selected_meeting(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
    recognition_log_id: int | None,
    captured_at: datetime | None = None,
    camera_id: int | None = None,
) -> int | None:
    """Tu dong check-in vao mot meeting duoc chi dinh."""
    now = captured_at or datetime.now(tz=timezone.utc)
    meeting = await get_meeting_or_404(db, meeting_id)
    ensure_meeting_matches_camera(meeting, camera_id)
    ensure_meeting_allows_recognition_checkin(meeting, now)
    return await try_auto_checkin(
        db=db,
        meeting=meeting,
        employee_id=employee_id,
        captured_at=now,
        recognition_log_id=recognition_log_id,
    )


async def apply_unknown_assignment_to_meetings(
    db: AsyncSession,
    employee_id: int,
    first_seen_at: datetime,
    camera_id: int | None = None,
) -> list[int]:
    """Cap nhat attendance meeting khi unknown queue duoc gan cho employee."""
    seen_at = as_aware_utc(first_seen_at)
    meetings = await repository.list_candidate_meetings_for_employee_seen_at(
        db=db,
        employee_id=employee_id,
        seen_at=seen_at,
        camera_id=camera_id,
    )
    updated: list[int] = []

    for meeting in meetings:
        result = await try_auto_checkin(
            db=db,
            meeting=meeting,
            employee_id=employee_id,
            captured_at=seen_at,
        )
        if result is not None:
            updated.append(result)

    return updated


async def try_auto_checkin(
    db: AsyncSession,
    meeting,
    employee_id: int,
    captured_at: datetime,
    recognition_log_id: int | None = None,
) -> int | None:
    """Thu auto check-in 1 participant vao 1 meeting, thanh cong thi tra meeting.id."""
    participant = await repository.get_meeting_participant(
        db=db,
        meeting_id=meeting.id,
        employee_id=employee_id,
    )

    if not participant:
        created = await repository.create_meeting_participants(
            db=db,
            meeting_id=meeting.id,
            employee_ids=[employee_id],
        )
        participant = created[0] if created else None
        if not participant:
            return None

    if participant.check_in_time is not None:
        return None
    if participant.status == ParticipantStatus.EXCUSED:
        return None

    status = derive_meeting_attendance_status(meeting, captured_at)
    await repository.update_participant_checkin(
        db=db,
        participant=participant,
        check_in_time=captured_at,
        check_in_log_id=recognition_log_id,
        status=status,
    )
    auto_start_meeting(meeting, status, captured_at)
    return meeting.id
