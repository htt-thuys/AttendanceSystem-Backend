from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, Form
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from infrastructure.database.models import User
from infrastructure.database.session import get_db
from modules.me import service
from modules.me.schemas import (
    MyPasswordUpdateRequest,
    MyProfileResponse,
    MyRecognitionLogItemResponse,
    SelfActionResponse,
)
from modules.meetings.schemas import (
    MeetingAbsenceRequest,
    MeetingActionResponse,
    MeetingCheckinRequest,
    MeetingCheckoutRequest,
)
from modules.meetings import service as meetings_service

router = APIRouter()


@router.get("/profile", response_model=MyProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.get_my_profile(db=db, current_user=current_user)


@router.patch("/profile", response_model=MyProfileResponse)
async def update_my_profile(
    full_name: str | None = Form(default=None),
    email: str | None = Form(default=None),
    avatar: UploadFile | None = File(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_my_profile(
        db=db,
        current_user=current_user,
        full_name=full_name,
        email=email,
        avatar=avatar,
    )


@router.patch("/password", response_model=SelfActionResponse)
async def update_my_password(
    payload: MyPasswordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.update_my_password(
        db=db,
        current_user=current_user,
        payload=payload,
    )


@router.get("/recognition-logs/today", response_model=list[MyRecognitionLogItemResponse])
async def get_my_recognition_logs_today(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await service.list_my_recognition_logs_today(
        db=db,
        current_user=current_user,
        limit=limit,
    )


@router.post("/meetings/{meeting_id}/checkin", response_model=MeetingActionResponse)
async def my_meeting_checkin(
    meeting_id: int,
    payload: MeetingCheckinRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nhân viên tự check-in vào cuộc họp."""
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="Tai khoan chua gan voi nhan vien")
    note = payload.note if payload else None
    return await meetings_service.checkin_participant(
        db=db,
        meeting_id=meeting_id,
        employee_id=current_user.employee_id,
        note=note,
    )


@router.post("/meetings/{meeting_id}/checkout", response_model=MeetingActionResponse)
async def my_meeting_checkout(
    meeting_id: int,
    payload: MeetingCheckoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nhân viên tự check-out khỏi cuộc họp."""
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="Tai khoan chua gan voi nhan vien")
    note = payload.note if payload else None
    return await meetings_service.checkout_participant(
        db=db,
        meeting_id=meeting_id,
        employee_id=current_user.employee_id,
        note=note,
    )


@router.post("/meetings/{meeting_id}/absence-request", response_model=MeetingActionResponse)
async def my_meeting_absence_request(
    meeting_id: int,
    payload: MeetingAbsenceRequest | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nhân viên tự xin vắng mặt có phép trước cuộc họp."""
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="Tai khoan chua gan voi nhan vien")
    note = payload.note if payload else None
    return await meetings_service.request_absence(
        db=db,
        meeting_id=meeting_id,
        employee_id=current_user.employee_id,
        note=note,
    )

