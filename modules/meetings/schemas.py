from datetime import datetime

from pydantic import BaseModel, Field


class MeetingActionResponse(BaseModel):
    """Schema tra ket qua thao tac lien quan cuoc hop."""

    success: bool
    message: str | None = None


class MeetingCreateRequest(BaseModel):
    """Schema tao cuoc hop moi."""

    title: str = Field(min_length=1)
    description: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime | None = None
    location: str | None = None
    camera_id: int | None = None
    employee_ids: list[int] = Field(default_factory=list)


class MeetingUpdateRequest(BaseModel):
    """Schema cap nhat thong tin cuoc hop."""

    title: str | None = None
    description: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    location: str | None = None
    camera_id: int | None = None
    status: str | None = None


class MeetingListItemResponse(BaseModel):
    """Schema hien thi danh sach cuoc hop."""

    id: int
    title: str
    scheduled_start: datetime
    scheduled_end: datetime | None = None


class MeetingCheckinRequest(BaseModel):
    """Schema yeu cau check-in cuoc hop (self-service)."""

    note: str | None = None


class MeetingCheckoutRequest(BaseModel):
    """Schema yeu cau check-out cuoc hop (self-service)."""

    note: str | None = None


class MeetingAbsenceRequest(BaseModel):
    """Schema yeu cau vang mat co phep truoc cuoc hop."""

    note: str | None = None


class MeetingParticipantResponse(BaseModel):
    """Schema hien thi mot nguoi tham gia cuoc hop."""

    id: int
    employee_id: int
    employee_name: str | None = None
    status: str
    check_in_time: datetime | None = None
    check_in_log_id: int | None = None
    check_out_time: datetime | None = None
    check_out_log_id: int | None = None
    note: str | None = None


class MeetingDetailResponse(BaseModel):
    """Schema tra ve chi tiet cuoc hop kem danh sach tham gia."""

    id: int
    title: str
    description: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    location: str | None = None
    camera_id: int | None = None
    status: str
    created_by: int
    created_at: datetime
    updated_at: datetime
    participants: list[MeetingParticipantResponse]


class MeetingParticipantsAddRequest(BaseModel):
    """Schema them hang loat nguoi tham gia."""

    employee_ids: list[int] = Field(min_length=1)


class MeetingAttendanceResponse(BaseModel):
    """Schema thong ke tinh trang diem danh cuoc hop."""

    meeting_id: int
    total_participants: int
    present_count: int
    late_count: int
    absent_count: int
    excused_count: int
    invited_count: int
    participants: list[MeetingParticipantResponse]


