from datetime import datetime

from pydantic import BaseModel, Field


class AdminActionResponse(BaseModel):
    """Schema tra ket qua chung cho cac thao tac admin don gian."""

    success: bool
    message: str | None = None
    employee_id: int | None = None


class UnknownQueueItemResponse(BaseModel):
    """Schema hien thi mot phan tu trong hang doi khuon mat chua nhan ra."""

    id: int
    camera_id: int | None = None
    event_id: int | None = None
    event_title: str | None = None
    meeting_id: int | None = None
    meeting_title: str | None = None
    image_path: str
    image_url: str | None = None
    attempt_count: int
    first_seen_at: datetime
    last_seen_at: datetime
    face_quality: float | None = None


class EmployeeListItemResponse(BaseModel):
    """Schema hien thi danh sach nhan vien phuc vu trang quan ly admin."""

    id: int
    full_name: str
    employee_code: str
    avatar_path: str | None = None
    avatar_url: str | None = None
    status: str
    vector_count: int


class EmployeeVectorItemResponse(BaseModel):
    """Schema hien thi mot vector cung anh nguon va diem so lien quan."""

    id: int
    source: str | None = None
    source_image_path: str
    source_image_url: str | None = None
    quality_score: float | None = None
    score_at_create: float | None = None
    created_at: datetime


class RuntimeSettingsResponse(BaseModel):
    """Schema tra ve cac nguong runtime ma server dang su dung."""

    sure_threshold: float
    review_low: float
    gap_min: float
    upsert_score_max: float
    upsert_min_vecs: int
    dedup_threshold: float
    image_retention_days: int
    recognition_log_cooldown_minutes: int
    event_tablet_lookahead_minutes: int


class RuntimeSettingsUpdateRequest(BaseModel):
    """Schema cap nhat mot phan hoac toan bo cac nguong runtime tu trang admin."""

    sure_threshold: float | None = Field(default=None, ge=0, le=1)
    review_low: float | None = Field(default=None, ge=0, le=1)
    gap_min: float | None = Field(default=None, ge=0, le=1)
    upsert_score_max: float | None = Field(default=None, ge=0, le=1)
    upsert_min_vecs: int | None = Field(default=None, ge=1)
    dedup_threshold: float | None = Field(default=None, ge=0, le=1)
    image_retention_days: int | None = Field(default=None, ge=1)
    recognition_log_cooldown_minutes: int | None = Field(default=None, ge=0)
    event_tablet_lookahead_minutes: int | None = Field(default=None, ge=0)


class CleanupRunResponse(BaseModel):
    """Schema tra ve ket qua sau khi admin chay cleanup bang tay."""

    success: bool
    deleted_recognition_log_images: int
    deleted_resolved_unknown_queue: int
    deleted_orphan_qdrant_points: int
    deleted_unreferenced_files: int
    auto_rejected_pending_recognition_logs: int
    deleted_rejected_recognition_logs: int
    deleted_read_notifications: int
    deleted_empty_storage_dirs: int
    retention_days: int


class RecognitionLogItemResponse(BaseModel):
    """Schema hien thi mot ban ghi recognition log cho trang log hoac lich su nhan vien."""

    id: int
    camera_id: int | None = None
    event_id: int | None = None
    event_title: str | None = None
    meeting_id: int | None = None
    meeting_title: str | None = None
    captured_at: datetime
    face_image_path: str | None = None
    face_image_url: str | None = None
    result_label: str | None = None
    top_score: float | None = None
    employee_id: int | None = None
    employee_name: str | None = None
    final_label: str | None = None
    resolved_at: datetime | None = None


class EmployeeAccountResponse(BaseModel):
    """Schema hien thi tai khoan dang nhap dang lien ket voi nhan vien."""

    user_id: int
    username: str
    email: str | None = None
    role: str
    is_active: bool
    employee_id: int | None = None
    created_at: datetime


class EmployeeAccountCreateRequest(BaseModel):
    """Schema tao tai khoan moi cho mot nhan vien tu man quan ly admin."""

    username: str
    email: str | None = None
    password: str = Field(min_length=6)
    role: str = Field(default="employee")


class UserPasswordUpdateRequest(BaseModel):
    """Schema doi hoac reset mat khau cho user do admin thuc hien."""

    password: str = Field(min_length=6)


class UserStatusUpdateRequest(BaseModel):
    """Schema khoa hoac mo lai trang thai hoat dong cua tai khoan."""

    is_active: bool
