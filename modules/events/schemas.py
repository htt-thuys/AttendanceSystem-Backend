from datetime import datetime

from pydantic import BaseModel, Field


class EventCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    starts_at: datetime
    ends_at: datetime


class EventUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    is_active: bool | None = None


class EventResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    created_by: int
    created_at: datetime
    updated_at: datetime


class EventBasicResponse(BaseModel):
    id: int
    title: str
    starts_at: datetime
    ends_at: datetime


class EventAttendanceLogResponse(BaseModel):
    id: int
    employee_id: int | None = None
    employee_name: str | None = None
    employee_code: str | None = None
    check_in_time: datetime
    status: str
    result_label: str | None = None
    final_label: str | None = None
    top_score: float | None = None
    face_image_path: str | None = None
    face_image_url: str | None = None


class EventAttendanceResponse(BaseModel):
    event_id: int
    title: str
    description: str | None = None
    starts_at: datetime
    ends_at: datetime
    is_active: bool
    total_logs: int
    total_recognized_employees: int
    present_count: int
    pending_count: int
    unknown_count: int
    rejected_count: int
    attendees: list[EventAttendanceLogResponse]
