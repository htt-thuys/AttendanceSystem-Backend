from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from modules.dashboard import repository
from modules.dashboard.schemas import (
    AttendanceTrendItem,
    AttendanceTrendResponse,
    CameraStatusItem,
    CameraStatusResponse,
    DashboardStatsResponse,
    LateArrivalItem,
    LateArrivalsResponse,
    RecognitionActivityItem,
    RecognitionActivityResponse,
)


async def get_dashboard_stats(db: AsyncSession) -> DashboardStatsResponse:
    """Lấy thống kê tổng quan cho dashboard."""
    today = date.today()
    total_employees = await repository.count_employees(db)
    attendance_today = await repository.count_attendance_today(db, today)
    recognition_today = await repository.count_recognition_today(db, today)
    unknown_faces = await repository.count_unknown_faces(db)
    return DashboardStatsResponse(
        total_employees=total_employees,
        attendance_today=attendance_today,
        recognition_today=recognition_today,
        unknown_faces=unknown_faces,
    )


async def get_attendance_trend(
    db: AsyncSession,
    date_from: date,
    date_to: date,
) -> AttendanceTrendResponse:
    """Lấy xu hướng điểm danh theo ngày."""
    _validate_range(date_from, date_to)
    rows = await repository.list_attendance_trend(db, date_from, date_to)
    items = [
        AttendanceTrendItem(
            date=row[0],
            on_time=int(row[1] or 0),
            late=int(row[2] or 0),
            absent=int(row[3] or 0),
            early_leave=int(row[4] or 0),
            half_day=int(row[5] or 0),
            excused=int(row[6] or 0),
        )
        for row in rows
    ]
    return AttendanceTrendResponse(date_from=date_from, date_to=date_to, items=items)


async def get_recognition_activity(
    db: AsyncSession,
    date_from: date,
    date_to: date,
) -> RecognitionActivityResponse:
    """Lấy hoạt động nhận diện theo ngày."""
    _validate_range(date_from, date_to)
    rows = await repository.list_recognition_activity(db, date_from, date_to)
    items = [RecognitionActivityItem(date=row[0], total=row[1]) for row in rows]
    return RecognitionActivityResponse(date_from=date_from, date_to=date_to, items=items)


async def get_late_arrivals(db: AsyncSession, target_date: date) -> LateArrivalsResponse:
    """Lấy danh sách nhân viên đi trễ trong ngày."""
    rows = await repository.list_late_arrivals(db, target_date)
    schedule = await repository.get_default_schedule(db)
    items = [
        LateArrivalItem(
            employee_id=record.employee_id,
            employee_name=employee_name,
            check_in_time=record.check_in_time,
            minutes_late=_compute_minutes_late(target_date, schedule, record.check_in_time),
        )
        for record, employee_name in rows
    ]
    return LateArrivalsResponse(date=target_date, items=items)


async def get_camera_status(db: AsyncSession) -> CameraStatusResponse:
    """Lấy trạng thái camera."""
    rows = await repository.list_camera_status(db)
    items = [
        CameraStatusItem(
            camera_id=camera.id,
            location=camera.location,
            is_active=camera.is_active,
            last_seen_at=last_seen,
        )
        for camera, last_seen in rows
    ]
    return CameraStatusResponse(items=items)


def _validate_range(date_from: date, date_to: date) -> None:
    """Kiểm tra khoảng ngày hợp lệ."""
    if date_from > date_to:
        raise HTTPException(status_code=400, detail="Ngày bắt đầu phải trước hoặc bằng ngày kết thúc")


def _compute_minutes_late(target_date: date, schedule, check_in_time: datetime | None) -> int | None:
    """Tính số phút đi trễ so với lịch làm việc."""
    if not check_in_time or not schedule:
        return None

    tzinfo = check_in_time.tzinfo
    schedule_start = datetime.combine(target_date, schedule.start_time)
    if tzinfo:
        schedule_start = schedule_start.replace(tzinfo=tzinfo)

    late_at = schedule_start + timedelta(minutes=schedule.late_threshold_minutes)
    if check_in_time <= late_at:
        return 0

    delta = check_in_time - late_at
    return int(delta.total_seconds() // 60)
