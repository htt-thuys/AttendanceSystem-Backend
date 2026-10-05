from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AttendanceRecord, Camera, Employee, RecognitionLog, UnknownQueue, WorkSchedule


async def count_employees(db: AsyncSession) -> int:
    """Đếm tổng số nhân viên."""
    query = select(func.count()).select_from(Employee).where(Employee.status != "deleted")
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def count_attendance_today(db: AsyncSession, target_date: date) -> int:
    """Đếm số nhân viên đã điểm danh hôm nay."""
    query = (
        select(func.count())
        .select_from(AttendanceRecord)
        .where(
            AttendanceRecord.date == target_date,
            AttendanceRecord.status.notin_(["absent", "excused"]),
        )
    )
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def count_recognition_today(db: AsyncSession, target_date: date) -> int:
    """Đếm số bản ghi nhận diện trong ngày."""
    start_dt, end_dt = _build_day_range(target_date)
    query = (
        select(func.count())
        .select_from(RecognitionLog)
        .where(RecognitionLog.captured_at >= start_dt, RecognitionLog.captured_at < end_dt)
    )
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def count_unknown_faces(db: AsyncSession) -> int:
    """Đếm số khuôn mặt lạ chưa xử lý."""
    query = select(func.count()).select_from(UnknownQueue).where(UnknownQueue.resolved_at.is_(None))
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def list_attendance_trend(
    db: AsyncSession,
    date_from: date,
    date_to: date,
) -> list[tuple[date, int, int, int, int, int, int]]:
    """Lấy thống kê điểm danh theo ngày."""
    query = (
        select(
            AttendanceRecord.date,
            func.sum(case((AttendanceRecord.status == "on_time", 1), else_=0)),
            func.sum(case((AttendanceRecord.status == "late", 1), else_=0)),
            func.sum(case((AttendanceRecord.status == "absent", 1), else_=0)),
            func.sum(case((AttendanceRecord.status == "early_leave", 1), else_=0)),
            func.sum(case((AttendanceRecord.status == "half_day", 1), else_=0)),
            func.sum(case((AttendanceRecord.status == "excused", 1), else_=0)),
        )
        .where(AttendanceRecord.date >= date_from, AttendanceRecord.date <= date_to)
        .group_by(AttendanceRecord.date)
        .order_by(AttendanceRecord.date.asc())
    )
    result = await db.execute(query)
    return list(result.all())


async def list_recognition_activity(
    db: AsyncSession,
    date_from: date,
    date_to: date,
) -> list[tuple[date, int]]:
    """Lấy thống kê hoạt động nhận diện theo ngày."""
    start_dt, _ = _build_day_range(date_from)
    _, end_dt = _build_day_range(date_to)
    query = (
        select(func.date(RecognitionLog.captured_at), func.count())
        .where(RecognitionLog.captured_at >= start_dt, RecognitionLog.captured_at < end_dt)
        .group_by(func.date(RecognitionLog.captured_at))
        .order_by(func.date(RecognitionLog.captured_at).asc())
    )
    result = await db.execute(query)
    return [(row[0], int(row[1])) for row in result.all()]


async def list_late_arrivals(
    db: AsyncSession,
    target_date: date,
) -> list[tuple[AttendanceRecord, str | None]]:
    """Lấy danh sách nhân viên đi trễ trong ngày."""
    query = (
        select(AttendanceRecord, Employee.full_name)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .where(AttendanceRecord.date == target_date, AttendanceRecord.status == "late")
        .order_by(AttendanceRecord.check_in_time.asc())
    )
    result = await db.execute(query)
    return list(result.all())


async def get_default_schedule(db: AsyncSession) -> WorkSchedule | None:
    """Lấy lịch làm việc mặc định."""
    query = select(WorkSchedule).where(WorkSchedule.is_default == True).order_by(WorkSchedule.id.asc())
    result = await db.execute(query)
    return result.scalars().first()


async def list_camera_status(db: AsyncSession) -> list[tuple[Camera, datetime | None]]:
    """Lấy trạng thái camera và thời gian nhận diện gần nhất."""
    latest_log_sub = (
        select(RecognitionLog.camera_id, func.max(RecognitionLog.captured_at).label("last_seen"))
        .group_by(RecognitionLog.camera_id)
        .subquery()
    )
    query = (
        select(Camera, latest_log_sub.c.last_seen)
        .outerjoin(latest_log_sub, latest_log_sub.c.camera_id == Camera.id)
        .order_by(Camera.id.asc())
    )
    result = await db.execute(query)
    return list(result.all())


def _build_day_range(target_date: date) -> tuple[datetime, datetime]:
    """Tạo khoảng thời gian [start, end) cho một ngày."""
    start_dt = datetime.combine(target_date, time.min)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt
