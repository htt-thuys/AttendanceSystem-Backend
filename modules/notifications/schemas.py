from datetime import datetime

from pydantic import BaseModel, Field


class NotificationItemResponse(BaseModel):
    """Schema một thông báo cho người dùng."""

    id: int
    type: str
    title: str
    message: str | None = None
    is_read: bool
    data: dict | None = None
    created_at: datetime
    read_at: datetime | None = None


class NotificationListResponse(BaseModel):
    """Schema danh sách thông báo có phân trang."""

    items: list[NotificationItemResponse]
    total: int
    page: int
    page_size: int


class NotificationReadResponse(BaseModel):
    """Schema phản hồi khi đọc thông báo."""

    success: bool
    message: str | None = None


class NotificationReadAllRequest(BaseModel):
    """Schema đánh dấu tất cả thông báo đã đọc."""

    include_read: bool = Field(default=False)


class NotificationUnreadCountResponse(BaseModel):
    """Schema số lượng thông báo chưa đọc."""

    unread_count: int
