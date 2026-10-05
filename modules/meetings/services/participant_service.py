"""Participant management use cases for meetings."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from modules.meetings import repository
from modules.meetings.enums import ParticipantStatus
from modules.meetings.helpers import count_participant_statuses
from modules.meetings.services.notification_service import (
    notify_meeting_participants,
)
from modules.meetings.schemas import (
    MeetingActionResponse,
    MeetingAttendanceResponse,
)
from modules.meetings.services.validators import (
    ensure_employees_exist,
    get_meeting_or_404,
    list_participants,
)


async def add_participants(
    db: AsyncSession,
    meeting_id: int,
    employee_ids: list[int],
) -> MeetingActionResponse:
    """Them nguoi tham gia vao meeting."""
    await get_meeting_or_404(db, meeting_id)
    clean_ids = sorted(
        {employee_id for employee_id in employee_ids if employee_id is not None}
    )
    if not clean_ids:
        raise HTTPException(
            status_code=400,
            detail="Danh sach nguoi tham gia dang rong",
        )

    await ensure_employees_exist(db, clean_ids)
    created_ids = [
        employee_id
        for employee_id in clean_ids
        if not await repository.get_meeting_participant(
            db=db,
            meeting_id=meeting_id,
            employee_id=employee_id,
        )
    ]

    if created_ids:
        await repository.create_meeting_participants(
            db=db,
            meeting_id=meeting_id,
            employee_ids=created_ids,
        )
        meeting = await get_meeting_or_404(db, meeting_id)
        await notify_meeting_participants(
            db=db,
            employee_ids=created_ids,
            title="Meeting invitation",
            message=f"You are invited to meeting: {meeting.title}",
            data={"meeting_id": meeting.id, "type": "meeting_invitation"},
        )
        await db.commit()

    return MeetingActionResponse(
        success=True,
        message="Da cap nhat danh sach tham gia",
    )


async def remove_participant(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
) -> MeetingActionResponse:
    """Xoa mot participant khoi meeting."""
    await get_meeting_or_404(db, meeting_id)
    await repository.delete_meeting_participant(
        db=db,
        meeting_id=meeting_id,
        employee_id=employee_id,
    )
    await db.commit()
    return MeetingActionResponse(success=True, message="Da xoa nguoi tham gia")


async def get_meeting_attendance(
    db: AsyncSession,
    meeting_id: int,
) -> MeetingAttendanceResponse:
    """Lay thong ke attendance cua meeting."""
    await get_meeting_or_404(db, meeting_id)
    participants = await list_participants(db, meeting_id)
    counts = count_participant_statuses(participants)

    return MeetingAttendanceResponse(
        meeting_id=meeting_id,
        total_participants=len(participants),
        present_count=counts.get(ParticipantStatus.PRESENT, 0),
        late_count=counts.get(ParticipantStatus.LATE, 0),
        absent_count=counts.get(ParticipantStatus.ABSENT, 0),
        excused_count=counts.get(ParticipantStatus.EXCUSED, 0),
        invited_count=counts.get(ParticipantStatus.INVITED, 0),
        participants=participants,
    )
