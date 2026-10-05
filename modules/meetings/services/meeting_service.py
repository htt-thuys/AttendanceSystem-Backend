"""Meeting CRUD and lifecycle service functions."""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from sqlalchemy import select
from infrastructure.database.models import User, Meeting
from modules.meetings import repository
from modules.meetings.enums import MeetingStatus
from modules.meetings.helpers import (
    as_aware_utc,
    build_meeting_detail_response,
    validate_meeting_status,
    validate_schedule,
)
from modules.meetings.services.notification_service import (
    notify_meeting_participants,
)
from modules.meetings.schemas import (
    MeetingActionResponse,
    MeetingCreateRequest,
    MeetingDetailResponse,
    MeetingListItemResponse,
    MeetingUpdateRequest,
)
from modules.meetings.services.validators import (
    ensure_camera_exists,
    ensure_employees_exist,
    get_meeting_or_404,
    list_participants,
)


async def auto_complete_expired_meetings(db: AsyncSession) -> int:
    """Tự động kết thúc các cuộc họp đã quá thời gian kết thúc dự kiến mà chưa được đóng."""
    now = datetime.now(tz=timezone.utc)
    result = await db.execute(
        select(Meeting).where(
            Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
            Meeting.scheduled_end.is_not(None),
            Meeting.scheduled_end < now,
        )
    )
    expired_meetings = list(result.scalars().all())
    if not expired_meetings:
        return 0

    count = 0
    for meeting in expired_meetings:
        meeting.status = MeetingStatus.COMPLETED
        meeting.actual_end = now
        await repository.mark_unchecked_participants_absent(
            db=db,
            meeting_id=meeting.id,
        )
        count += 1

    await db.commit()
    return count


async def list_meetings(
    db: AsyncSession,
    date_from=None,
    date_to=None,
    status: str | None = None,
) -> list[MeetingListItemResponse]:
    """Lay danh sach meeting theo bo loc."""
    await auto_complete_expired_meetings(db)
    rows = await repository.list_meeting_records(
        db=db,
        date_from=date_from,
        date_to=date_to,
        status=status,
    )
    return [
        MeetingListItemResponse(
            id=meeting.id,
            title=meeting.title,
            scheduled_start=meeting.scheduled_start,
            scheduled_end=meeting.scheduled_end,
            location=meeting.location,
            camera_id=meeting.camera_id,
            status=meeting.status,
            participant_count=int(count),
            created_by=meeting.created_by,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )
        for meeting, count in rows
    ]


async def list_active_public_meetings(
    db: AsyncSession,
) -> list[MeetingListItemResponse]:
    """Lấy danh sách các cuộc họp đang/sắp hoạt động công khai để máy check-in hiển thị."""
    await auto_complete_expired_meetings(db)
    now = datetime.now(tz=timezone.utc)
    rows = await repository.list_active_public_meeting_records(db=db, now=now)
    
    return [
        MeetingListItemResponse(
            id=meeting.id,
            title=meeting.title,
            scheduled_start=meeting.scheduled_start,
            scheduled_end=meeting.scheduled_end,
            location=meeting.location,
            camera_id=meeting.camera_id,
            status=meeting.status,
            participant_count=int(count),
            created_by=meeting.created_by,
            created_at=meeting.created_at,
            updated_at=meeting.updated_at,
        )
        for meeting, count in rows
    ]



async def get_meeting_detail(
    db: AsyncSession,
    meeting_id: int,
) -> MeetingDetailResponse:
    """Lay chi tiet meeting kem participant."""
    meeting = await get_meeting_or_404(db, meeting_id)
    participants = await list_participants(db, meeting_id)
    return build_meeting_detail_response(meeting, participants)


async def create_meeting(
    db: AsyncSession,
    payload: MeetingCreateRequest,
    current_user: User,
) -> MeetingDetailResponse:
    """Tao meeting moi va moi participant neu co."""
    validate_schedule(payload.scheduled_start, payload.scheduled_end)

    if payload.camera_id is not None:
        await ensure_camera_exists(db, payload.camera_id)

    clean_ids = sorted(
        {employee_id for employee_id in payload.employee_ids if employee_id is not None}
    )
    if clean_ids:
        await ensure_employees_exist(db, clean_ids)

    meeting = await repository.create_meeting_record(
        db=db,
        title=payload.title,
        description=payload.description,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        location=payload.location,
        camera_id=payload.camera_id,
        created_by=current_user.id,
    )

    if clean_ids:
        await repository.create_meeting_participants(
            db=db,
            meeting_id=meeting.id,
            employee_ids=clean_ids,
        )
        await notify_meeting_participants(
            db=db,
            employee_ids=clean_ids,
            title="Meeting invitation",
            message=f"You are invited to meeting: {meeting.title}",
            data={"meeting_id": meeting.id, "type": "meeting_invitation"},
        )

    await db.commit()
    await db.refresh(meeting)
    participants = await list_participants(db, meeting.id)
    return build_meeting_detail_response(meeting, participants)


async def update_meeting(
    db: AsyncSession,
    meeting_id: int,
    payload: MeetingUpdateRequest,
) -> MeetingDetailResponse:
    """Cap nhat thong tin meeting."""
    meeting = await get_meeting_or_404(db, meeting_id)

    if payload.status:
        validate_meeting_status(payload.status)
        meeting.status = payload.status

    for attr in (
        "title",
        "description",
        "scheduled_start",
        "scheduled_end",
        "actual_start",
        "actual_end",
        "location",
    ):
        value = getattr(payload, attr, None)
        if value is not None:
            setattr(meeting, attr, value)

    if payload.camera_id is not None:
        await ensure_camera_exists(db, payload.camera_id)
        meeting.camera_id = payload.camera_id

    validate_schedule(meeting.scheduled_start, meeting.scheduled_end)
    await db.commit()
    await db.refresh(meeting)

    participants = await list_participants(db, meeting.id)
    return build_meeting_detail_response(meeting, participants)


async def cancel_meeting(
    db: AsyncSession,
    meeting_id: int,
) -> MeetingActionResponse:
    """Huy meeting."""
    meeting = await get_meeting_or_404(db, meeting_id)
    meeting.status = MeetingStatus.CANCELLED
    await db.commit()
    return MeetingActionResponse(success=True, message="Da huy cuoc hop")


async def complete_meeting(
    db: AsyncSession,
    meeting_id: int,
) -> MeetingActionResponse:
    """Ket thuc meeting va danh dau invited chua check-in la absent."""
    meeting = await get_meeting_or_404(db, meeting_id)
    if meeting.status == MeetingStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cuoc hop da bi huy")

    now = datetime.now(tz=timezone.utc)
    if meeting.scheduled_end is not None and now < as_aware_utc(meeting.scheduled_end):
        raise HTTPException(
            status_code=400,
            detail="Chua den gio ket thuc cuoc hop",
        )

    meeting.status = MeetingStatus.COMPLETED
    meeting.actual_end = now
    affected = await repository.mark_unchecked_participants_absent(
        db=db,
        meeting_id=meeting_id,
    )
    await db.commit()

    return MeetingActionResponse(
        success=True,
        message=f"Da ket thuc cuoc hop, danh dau {affected} nguoi vang mat",
    )
