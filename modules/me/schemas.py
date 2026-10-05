from datetime import datetime

from pydantic import BaseModel, Field


class SelfActionResponse(BaseModel):
    """Schema tra ket qua chung cho cac thao tac self-service cua user hien tai."""

    success: bool
    message: str | None = None


class MyProfileResponse(BaseModel):
    """Schema tra thong tin ho so hien tai cua user va nhan vien lien ket neu co."""

    user_id: int
    username: str
    email: str | None = None
    role: str
    is_active: bool
    employee_id: int | None = None
    full_name: str | None = None
    employee_code: str | None = None
    avatar_path: str | None = None
    avatar_url: str | None = None
    employee_status: str | None = None
    created_at: datetime


class MyPasswordUpdateRequest(BaseModel):
    """Schema doi mat khau cua chinh user hien tai."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(min_length=6)


class MyRecognitionLogItemResponse(BaseModel):
    """Schema hien thi log nhan dien hom nay cua chinh user hien tai."""

    id: int
    camera_id: int | None = None
    captured_at: datetime
    face_image_path: str | None = None
    face_image_url: str | None = None
    result_label: str | None = None
    top_score: float | None = None
    final_label: str | None = None
    resolved_at: datetime | None = None
