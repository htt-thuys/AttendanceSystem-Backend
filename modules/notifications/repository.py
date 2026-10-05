from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Notification


async def list_notifications(
    db: AsyncSession,
    user_id: int,
    is_read: bool | None,
    offset: int,
    limit: int,
) -> list[Notification]:
    """Lấy danh sách thông báo theo user và trạng thái đọc."""
    query = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_notifications(
    db: AsyncSession,
    user_id: int,
    is_read: bool | None,
) -> int:
    """Đếm số lượng thông báo theo trạng thái đọc."""
    query = select(func.count()).select_from(Notification).where(Notification.user_id == user_id)
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def get_notification(db: AsyncSession, user_id: int, notification_id: int) -> Notification | None:
    """Lấy thông báo theo id của user."""
    query = select(Notification).where(Notification.id == notification_id, Notification.user_id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def mark_notification_read(
    db: AsyncSession,
    notification: Notification,
    read_time: datetime,
) -> None:
    """Đánh dấu một thông báo đã đọc."""
    notification.is_read = True
    notification.read_at = read_time


async def mark_all_read(db: AsyncSession, user_id: int, read_time: datetime, include_read: bool) -> int:
    """Đánh dấu tất cả thông báo của user đã đọc."""
    query = update(Notification).where(Notification.user_id == user_id)
    if not include_read:
        query = query.where(Notification.is_read == False)
    query = query.values(is_read=True, read_at=read_time)
    result = await db.execute(query)
    return int(result.rowcount or 0)
