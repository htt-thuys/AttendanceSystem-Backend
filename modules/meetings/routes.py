from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.meetings import service
from modules.meetings.schemas import (
    MeetingActionResponse,
    MeetingAttendanceResponse,
    MeetingCreateRequest,
    MeetingDetailResponse,
    MeetingListItemResponse,
    MeetingParticipantsAddRequest,
    MeetingUpdateRequest,
)

router = APIRouter()


@router.post("/meetings", response_model=MeetingDetailResponse)
async def create_meeting(
    payload: MeetingCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_roles("admin")),
):
    return await service.create_meeting(db=db, payload=payload, current_user=current_user)


@router.get("/meetings", response_model=list[MeetingListItemResponse])
async def list_meetings(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.list_meetings(db=db, date_from=date_from, date_to=date_to, status=status)


@router.get("/meetings/list-public", response_model=list[MeetingListItemResponse])
async def list_active_public_meetings(
    db: AsyncSession = Depends(get_db),
):
    """Lấy danh sách các cuộc họp đang/sắp hoạt động công khai để máy check-in hiển thị."""
    return await service.list_active_public_meetings(db=db)



@router.get("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def get_meeting_detail(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.get_meeting_detail(db=db, meeting_id=meeting_id)


@router.patch("/meetings/{meeting_id}", response_model=MeetingDetailResponse)
async def update_meeting(
    meeting_id: int,
    payload: MeetingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.update_meeting(db=db, meeting_id=meeting_id, payload=payload)


@router.delete("/meetings/{meeting_id}", response_model=MeetingActionResponse)
async def cancel_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.cancel_meeting(db=db, meeting_id=meeting_id)


@router.post("/meetings/{meeting_id}/complete", response_model=MeetingActionResponse)
async def complete_meeting(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Admin kết thúc meeting và finalize trạng thái absent."""
    return await service.complete_meeting(db=db, meeting_id=meeting_id)


@router.post("/meetings/{meeting_id}/participants", response_model=MeetingActionResponse)
async def add_meeting_participants(
    meeting_id: int,
    payload: MeetingParticipantsAddRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.add_participants(db=db, meeting_id=meeting_id, employee_ids=payload.employee_ids)


@router.delete("/meetings/{meeting_id}/participants/{emp_id}", response_model=MeetingActionResponse)
async def remove_meeting_participant(
    meeting_id: int,
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.remove_participant(db=db, meeting_id=meeting_id, employee_id=emp_id)


@router.get("/meetings/{meeting_id}/attendance", response_model=MeetingAttendanceResponse)
async def get_meeting_attendance(
    meeting_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.get_meeting_attendance(db=db, meeting_id=meeting_id)

