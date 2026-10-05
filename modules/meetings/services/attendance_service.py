"""Manual attendance actions for meeting participants."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from modules.meetings import repository
from modules.meetings.enums import (
    ABSENCE_REQUEST_MIN_NOTICE,
    CHECKOUT_ALLOWED_STATUSES,
    MeetingStatus,
    ParticipantStatus,
)
from modules.meetings.helpers import (
    as_aware_utc,
    build_checkin_message,
    derive_meeting_attendance_status,
    ensure_meeting_allows_checkin,
)
from modules.meetings.schemas import MeetingActionResponse
from modules.meetings.services.validators import (
    get_meeting_or_404,
    get_participant_or_404,
)


def auto_start_meeting(meeting, checkin_status: str, now: datetime) -> None:
    """Tu chuyen meeting sang in_progress khi co check-in dau tien."""
    if (
        meeting.status == MeetingStatus.SCHEDULED
        and checkin_status != ParticipantStatus.ABSENT
    ):
        meeting.status = MeetingStatus.IN_PROGRESS
        meeting.actual_start = now


async def checkin_participant(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
    note: str | None = None,
) -> MeetingActionResponse:
    """Diem danh check-in thu cong cho participant."""
    meeting = await get_meeting_or_404(db, meeting_id)
    ensure_meeting_allows_checkin(meeting)

    participant = await repository.get_meeting_participant(
        db=db,
        meeting_id=meeting_id,
        employee_id=employee_id,
    )
    if not participant:
        created = await repository.create_meeting_participants(
            db=db,
            meeting_id=meeting_id,
            employee_ids=[employee_id],
        )
        participant = created[0] if created else None
        if not participant:
            raise HTTPException(
                status_code=500,
                detail="Không thể khởi tạo thông tin tham gia cuộc họp",
            )

    if participant.check_in_time is not None:
        raise HTTPException(status_code=400, detail="Nhan vien da check-in truoc do")
    if participant.status == ParticipantStatus.EXCUSED:
        raise HTTPException(
            status_code=400,
            detail="Nhan vien da xin vang mat co phep",
        )

    now = datetime.now(tz=timezone.utc)
    checkin_status = derive_meeting_attendance_status(meeting, now)
    await repository.update_participant_checkin(
        db=db,
        participant=participant,
        check_in_time=now,
        note=note,
        status=checkin_status,
    )
    auto_start_meeting(meeting, checkin_status, now)
    await db.commit()

    return MeetingActionResponse(
        success=True,
        message=build_checkin_message(meeting.title, checkin_status),
    )


async def checkout_participant(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
    note: str | None = None,
) -> MeetingActionResponse:
    """Ghi nhan check-out cho participant."""
    meeting = await get_meeting_or_404(db, meeting_id)
    if meeting.status not in CHECKOUT_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Cuoc hop chua bat dau hoac da bi huy, khong the check-out",
        )

    participant = await get_participant_or_404(db, meeting_id, employee_id)
    if participant.check_in_time is None:
        raise HTTPException(
            status_code=400,
            detail="Nhan vien chua check-in, khong the check-out",
        )
    if participant.check_out_time is not None:
        raise HTTPException(
            status_code=400,
            detail="Nhan vien da check-out truoc do",
        )

    now = datetime.now(tz=timezone.utc)
    await repository.update_participant_checkout(
        db=db,
        participant=participant,
        check_out_time=now,
        note=note,
    )
    await db.commit()
    return MeetingActionResponse(success=True, message="Check-out thanh cong")


async def request_absence(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
    note: str | None = None,
) -> MeetingActionResponse:
    """Ghi nhan xin vang mat co phep truoc meeting."""
    meeting = await get_meeting_or_404(db, meeting_id)
    participant = await get_participant_or_404(db, meeting_id, employee_id)

    if participant.check_in_time is not None:
        raise HTTPException(
            status_code=400,
            detail="Nhan vien da check-in, khong the xin vang mat",
        )

    now = datetime.now(tz=timezone.utc)
    deadline = as_aware_utc(meeting.scheduled_start) - ABSENCE_REQUEST_MIN_NOTICE
    if now > deadline:
        raise HTTPException(
            status_code=400,
            detail="Chi duoc xin vang mat truoc gio bat dau it nhat 30 phut",
        )

    await repository.update_participant_status(
        db=db,
        participant=participant,
        status=ParticipantStatus.EXCUSED,
        note=note,
    )
    await db.commit()
    return MeetingActionResponse(success=True, message="Da ghi nhan vang mat co phep")
