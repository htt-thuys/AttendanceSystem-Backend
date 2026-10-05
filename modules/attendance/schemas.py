from datetime import date, datetime

from pydantic import BaseModel, Field


class AttendanceMeetingInfo(BaseModel):
    """Schema thông tin cuộc họp đã điểm danh trong ngày."""

    id: int
    title: str
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    status: str


class AttendanceEventInfo(BaseModel):
    """Schema thông tin sự kiện đã điểm danh trong ngày."""

    id: int
    title: str
    check_in_time: datetime


class AttendanceListItemResponse(BaseModel):
    """Schema dòng điểm danh hiển thị cho danh sách."""

    id: int
    employee_id: int
    employee_name: str | None = None
    date: date
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    status: str
    work_hours: float | None = None
    note: str | None = None
    meetings: list[AttendanceMeetingInfo] = []
    events: list[AttendanceEventInfo] = []


class AttendanceStatsResponse(BaseModel):
    """Schema thống kê tổng hợp theo trạng thái điểm danh."""

    total_employees: int
    present_count: int
    late_count: int
    absent_count: int
    excused_count: int
    on_time_count: int
    early_leave_count: int
    half_day_count: int


class AttendanceTodaySummaryResponse(BaseModel):
    """Schema tổng hợp điểm danh trong ngày."""

    date: date
    stats: AttendanceStatsResponse


class AttendanceReportResponse(BaseModel):
    """Schema báo cáo điểm danh theo khoảng ngày."""

    date_from: date
    date_to: date
    stats: AttendanceStatsResponse
    records: list[AttendanceListItemResponse]


class AttendanceExportRequest(BaseModel):
    """Schema tham số export điểm danh."""

    date_from: date | None = None
    date_to: date | None = None
    employee_id: int | None = None
    status: str | None = None
    format: str = Field(default="csv", min_length=1)


class AttendanceAbsenceRequest(BaseModel):
    """Schema yêu cầu báo vắng có phép cho điểm danh hàng ngày."""

    date: date
    reason: str = Field(min_length=1, max_length=500)


class AttendanceUpdateNoteRequest(BaseModel):
    """Schema admin cập nhật trạng thái/ghi chú điểm danh."""

    status: str | None = None
    note: str | None = None
