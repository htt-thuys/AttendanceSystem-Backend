from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from infrastructure.database.models import User
from infrastructure.database.session import get_db
from modules.notifications import service
from modules.notifications.schemas import (
    NotificationListResponse,
    NotificationReadAllRequest,
    NotificationReadResponse,
    NotificationUnreadCountResponse,
)

router = APIRouter()


@router.get("/me/notifications", response_model=NotificationListResponse)
async def list_my_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    is_read: bool | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy danh sách thông báo của user đang đăng nhập."""
    return await service.list_my_notifications(
        db=db,
        current_user=current_user,
        page=page,
        page_size=page_size,
        is_read=is_read,
    )


@router.get("/me/notifications/unread-count", response_model=NotificationUnreadCountResponse)
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lấy số lượng thông báo chưa đọc."""
    return await service.get_unread_count(db=db, current_user=current_user)


@router.patch("/me/notifications/{notification_id}/read", response_model=NotificationReadResponse)
async def mark_notification_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Đánh dấu một thông báo đã đọc."""
    return await service.mark_notification_read(
        db=db,
        current_user=current_user,
        notification_id=notification_id,
    )


@router.post("/me/notifications/read-all", response_model=NotificationReadResponse)
async def mark_all_read(
    payload: NotificationReadAllRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Đánh dấu tất cả thông báo đã đọc."""
    return await service.mark_all_read(db=db, current_user=current_user, payload=payload)
