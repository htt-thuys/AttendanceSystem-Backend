"""Validation and lookup helpers for the meetings service layer."""

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from modules.meetings import repository
from modules.meetings.schemas import MeetingParticipantResponse


async def get_meeting_or_404(db: AsyncSession, meeting_id: int):
    """Lay cuoc hop theo id hoac raise 404."""
    meeting = await repository.get_meeting_record(db=db, meeting_id=meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Khong tim thay cuoc hop")
    return meeting


async def get_participant_or_404(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
):
    """Lay participant cua meeting hoac raise 404."""
    participant = await repository.get_meeting_participant(
        db=db,
        meeting_id=meeting_id,
        employee_id=employee_id,
    )
    if not participant:
        raise HTTPException(
            status_code=404,
            detail="Nhan vien khong nam trong danh sach tham gia cuoc hop nay",
        )
    return participant


async def list_participants(
    db: AsyncSession,
    meeting_id: int,
) -> list[MeetingParticipantResponse]:
    """Lay danh sach participant dang response schema."""
    rows = await repository.list_meeting_participants(db=db, meeting_id=meeting_id)
    return [
        MeetingParticipantResponse(
            id=participant.id,
            employee_id=participant.employee_id,
            employee_name=employee_name,
            status=participant.status,
            check_in_time=participant.check_in_time,
            check_in_log_id=participant.check_in_log_id,
            check_out_time=participant.check_out_time,
            check_out_log_id=participant.check_out_log_id,
            note=participant.note,
        )
        for participant, employee_name in rows
    ]


async def ensure_camera_exists(db: AsyncSession, camera_id: int) -> None:
    """Dam bao camera ton tai."""
    if not await repository.get_camera_record(db=db, camera_id=camera_id):
        raise HTTPException(status_code=400, detail="Khong tim thay camera")


async def ensure_employees_exist(
    db: AsyncSession,
    employee_ids: list[int],
) -> None:
    """Dam bao toan bo employee_id ton tai va chua bi xoa."""
    existing = await repository.list_existing_employee_ids(
        db=db,
        employee_ids=employee_ids,
    )
    if any(employee_id not in existing for employee_id in employee_ids):
        raise HTTPException(status_code=400, detail="Co nhan vien khong ton tai")
