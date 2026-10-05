from pydantic import BaseModel


class ConfirmRequest(BaseModel):
    """Schema nhan du lieu confirm tu FE, gom action va employee_id neu can."""

    recognition_log_id: int
    action: str
    employee_id: int | None = None
    meeting_id: int | None = None
    event_id: int | None = None


class ConfirmResponse(BaseModel):
    """Schema tra ket qua confirm don gian cho FE."""

    success: bool
    message: str | None = None
