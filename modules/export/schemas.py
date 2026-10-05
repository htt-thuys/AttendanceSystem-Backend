from datetime import date

from pydantic import BaseModel, Field


class AttendanceExportRequest(BaseModel):
    """Schema tham số export điểm danh."""

    date_from: date | None = None
    date_to: date | None = None
    employee_id: int | None = None
    status: str | None = None
    format: str = Field(default="csv", min_length=1)


class RecognitionLogsExportRequest(BaseModel):
    """Schema tham số export nhật ký nhận diện."""

    date_from: date | None = None
    date_to: date | None = None
    employee_id: int | None = None
    camera_id: int | None = None
    event_id: int | None = None
    result_label: str | None = None
    final_label: str | None = None
    format: str = Field(default="csv", min_length=1)


class EmployeesExportRequest(BaseModel):
    """Schema tham số export danh sách nhân viên."""

    status: str | None = None
    format: str = Field(default="csv", min_length=1)
