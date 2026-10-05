from pydantic import BaseModel


class Candidate(BaseModel):
    """Schema ung vien goi y cho FE chon lai khi can review."""

    employee_id: int
    score: float


class EmployeeBasic(BaseModel):
    """Schema thong tin nhan vien co ban tra ve cho FE."""

    id: int
    full_name: str


class EventBasic(BaseModel):
    """Schema thong tin event dang active cho tablet popup."""

    id: int
    title: str


class MeetingBasic(BaseModel):
    """Schema thong tin meeting dang active cho tablet popup."""

    id: int
    title: str


class RecognizeResponse(BaseModel):
    """Schema ket qua nhan dien khuon mat tra ve tu API recognize."""

    label: str
    recognition_log_id: int | None = None
    employee: EmployeeBasic | None = None
    score: float | None = None
    candidates: list[Candidate] | None = None
    auto_attendance: bool | None = None
    auto_meeting_checkin: int | None = None
    event_id: int | None = None
    event: EventBasic | None = None
    meeting_id: int | None = None
    meeting: MeetingBasic | None = None
    log_saved: bool | None = None
    live_score: float | None = None
    spoof_score: float | None = None
