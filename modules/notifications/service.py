from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Notification, User
from modules.notifications import repository
from modules.notifications.schemas import (
    NotificationItemResponse,
    NotificationListResponse,
    NotificationReadAllRequest,
    NotificationReadResponse,
    NotificationUnreadCountResponse,
)


async def list_my_notifications(
    db: AsyncSession,
    current_user: User,
    page: int,
    page_size: int,
    is_read: bool | None,
) -> NotificationListResponse:
    """Lấy danh sách thông báo của user đang đăng nhập."""
    if page < 1 or page_size < 1:
        raise HTTPException(status_code=400, detail="Trang và kích thước trang phải lớn hơn 0")

    offset = (page - 1) * page_size
    total = await repository.count_notifications(db=db, user_id=current_user.id, is_read=is_read)
    rows = await repository.list_notifications(
        db=db,
        user_id=current_user.id,
        is_read=is_read,
        offset=offset,
        limit=page_size,
    )

    items = [_build_notification_item(item) for item in rows]
    return NotificationListResponse(items=items, total=total, page=page, page_size=page_size)


async def get_unread_count(db: AsyncSession, current_user: User) -> NotificationUnreadCountResponse:
    """Lấy số lượng thông báo chưa đọc."""
    total = await repository.count_notifications(db=db, user_id=current_user.id, is_read=False)
    return NotificationUnreadCountResponse(unread_count=total)


async def mark_notification_read(
    db: AsyncSession,
    current_user: User,
    notification_id: int,
) -> NotificationReadResponse:
    """Đánh dấu một thông báo đã đọc."""
    notification = await repository.get_notification(db, current_user.id, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")

    if notification.is_read:
        return NotificationReadResponse(success=True, message="Thông báo đã được đọc trước đó")

    await repository.mark_notification_read(db, notification, datetime.utcnow())
    await db.commit()
    return NotificationReadResponse(success=True, message="Đã đánh dấu thông báo đã đọc")


async def mark_all_read(
    db: AsyncSession,
    current_user: User,
    payload: NotificationReadAllRequest,
) -> NotificationReadResponse:
    """Đánh dấu tất cả thông báo đã đọc."""
    affected = await repository.mark_all_read(
        db=db,
        user_id=current_user.id,
        read_time=datetime.utcnow(),
        include_read=payload.include_read,
    )
    await db.commit()
    return NotificationReadResponse(success=True, message=f"Đã đánh dấu {affected} thông báo")


def _build_notification_item(notification: Notification) -> NotificationItemResponse:
    """Chuyển notification ORM sang response."""
    return NotificationItemResponse(
        id=notification.id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        data=notification.data,
        created_at=notification.created_at,
        read_at=notification.read_at,
    )
