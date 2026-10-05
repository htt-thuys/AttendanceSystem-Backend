from datetime import date, datetime

from pydantic import BaseModel


class DashboardStatsResponse(BaseModel):
    """Schema thống kê tổng quan cho dashboard."""

    total_employees: int
    attendance_today: int
    recognition_today: int
    unknown_faces: int


class AttendanceTrendItem(BaseModel):
    """Schema một điểm dữ liệu xu hướng điểm danh."""

    date: date
    on_time: int
    late: int
    absent: int
    early_leave: int
    half_day: int
    excused: int


class AttendanceTrendResponse(BaseModel):
    """Schema xu hướng điểm danh."""

    date_from: date
    date_to: date
    items: list[AttendanceTrendItem]


class RecognitionActivityItem(BaseModel):
    """Schema một điểm dữ liệu hoạt động nhận diện."""

    date: date
    total: int


class RecognitionActivityResponse(BaseModel):
    """Schema hoạt động nhận diện theo thời gian."""

    date_from: date
    date_to: date
    items: list[RecognitionActivityItem]


class LateArrivalItem(BaseModel):
    """Schema danh sách đi trễ hôm nay."""

    employee_id: int
    employee_name: str | None = None
    check_in_time: datetime | None = None
    minutes_late: int | None = None


class LateArrivalsResponse(BaseModel):
    """Schema danh sách đi trễ hôm nay."""

    date: date
    items: list[LateArrivalItem]


class CameraStatusItem(BaseModel):
    """Schema trạng thái camera."""

    camera_id: int
    location: str | None = None
    is_active: bool
    last_seen_at: datetime | None = None


class CameraStatusResponse(BaseModel):
    """Schema tổng hợp trạng thái camera."""

    items: list[CameraStatusItem]
