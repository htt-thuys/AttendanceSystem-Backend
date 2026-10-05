from __future__ import annotations

from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import (
    AttendanceRecord,
    Employee,
    RecognitionLog,
    WorkSchedule,
    Meeting,
    MeetingParticipant,
    Event,
)
from modules.attendance.enums import EmployeeStatus, RecognitionLabel
from modules.attendance.helpers import LOCAL_TZ


async def list_attendance_records(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
    employee_id: int | None = None,
    status: str | None = None,
) -> list[tuple[AttendanceRecord, str | None]]:
    """Lấy danh sách bản ghi điểm danh kèm tên nhân viên."""
    query = (
        select(AttendanceRecord, Employee.full_name)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .where(Employee.status != EmployeeStatus.DELETED)
        .order_by(AttendanceRecord.date.desc(), AttendanceRecord.id.desc())
    )

    conditions = []
    if date_from:
        conditions.append(AttendanceRecord.date >= date_from)
    if date_to:
        conditions.append(AttendanceRecord.date <= date_to)
    if employee_id:
        conditions.append(AttendanceRecord.employee_id == employee_id)
    if status:
        conditions.append(AttendanceRecord.status == status)
    if conditions:
        query = query.where(*conditions)

    result = await db.execute(query)
    return list(result.all())


async def get_attendance_record(
    db: AsyncSession,
    employee_id: int,
    target_date: date,
) -> AttendanceRecord | None:
    """Lấy bản ghi điểm danh theo nhân viên và ngày."""
    query = select(AttendanceRecord).where(
        AttendanceRecord.employee_id == employee_id,
        AttendanceRecord.date == target_date,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_attendance_record_by_id(
    db: AsyncSession,
    record_id: int,
) -> AttendanceRecord | None:
    """Lấy bản ghi điểm danh theo id."""
    query = select(AttendanceRecord).where(AttendanceRecord.id == record_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_attendance_record(
    db: AsyncSession,
    employee_id: int,
    target_date: date,
    check_in_time: datetime | None,
    check_out_time: datetime | None,
    check_in_log_id: int | None,
    check_out_log_id: int | None,
    status: str,
    work_hours: float | None,
    note: str | None = None,
) -> AttendanceRecord:
    """Tạo bản ghi điểm danh mới cho nhân viên."""
    record = AttendanceRecord(
        employee_id=employee_id,
        date=target_date,
        check_in_time=check_in_time,
        check_out_time=check_out_time,
        check_in_log_id=check_in_log_id,
        check_out_log_id=check_out_log_id,
        status=status,
        work_hours=work_hours,
        note=note,
    )
    db.add(record)
    await db.flush()
    return record


async def list_active_employees(db: AsyncSession) -> list[Employee]:
    """Lấy danh sách nhân viên đang hoạt động."""
    query = select(Employee).where(Employee.status == EmployeeStatus.ACTIVE).order_by(Employee.id.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_employee_by_id(db: AsyncSession, employee_id: int) -> Employee | None:
    """Lấy thông tin nhân viên theo id."""
    query = select(Employee).where(Employee.id == employee_id, Employee.status != EmployeeStatus.DELETED)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def list_confirmed_logs_for_employee_date(
    db: AsyncSession,
    employee_id: int,
    target_date: date,
) -> list[RecognitionLog]:
    """Lấy các log đã xác nhận của nhân viên trong ngày."""
    start_dt, end_dt = _build_day_range(target_date)
    query = (
        select(RecognitionLog)
        .where(
            RecognitionLog.employee_id == employee_id,
            RecognitionLog.final_label == RecognitionLabel.CONFIRMED,
            RecognitionLog.captured_at >= start_dt,
            RecognitionLog.captured_at < end_dt,
        )
        .order_by(RecognitionLog.captured_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_default_schedule(db: AsyncSession) -> WorkSchedule | None:
    """Lấy lịch làm việc mặc định nếu có."""
    query = select(WorkSchedule).where(WorkSchedule.is_default == True).order_by(WorkSchedule.id.asc())
    result = await db.execute(query)
    return result.scalars().first()


async def list_confirmed_logs_for_date_range(
    db: AsyncSession,
    employee_ids: list[int],
    date_from: date,
    date_to: date,
) -> list[RecognitionLog]:
    """Batch lấy tất cả confirmed logs trong khoảng ngày cho nhiều nhân viên."""
    start_dt, _ = _build_day_range(date_from)
    _, end_dt = _build_day_range(date_to)
    query = (
        select(RecognitionLog)
        .where(
            RecognitionLog.employee_id.in_(employee_ids),
            RecognitionLog.final_label == RecognitionLabel.CONFIRMED,
            RecognitionLog.captured_at >= start_dt,
            RecognitionLog.captured_at < end_dt,
        )
        .order_by(RecognitionLog.employee_id, RecognitionLog.captured_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def list_existing_attendance_records(
    db: AsyncSession,
    employee_ids: list[int],
    date_from: date,
    date_to: date,
) -> list[AttendanceRecord]:
    """Batch lấy tất cả attendance records trong khoảng ngày."""
    query = select(AttendanceRecord).where(
        AttendanceRecord.employee_id.in_(employee_ids),
        AttendanceRecord.date >= date_from,
        AttendanceRecord.date <= date_to,
    )
    result = await db.execute(query)
    return list(result.scalars().all())


def _build_day_range(target_date: date) -> tuple[datetime, datetime]:
    """Tạo khoảng thời gian [start, end) cho một ngày (timezone-aware)."""
    start_dt = datetime.combine(target_date, time.min, tzinfo=LOCAL_TZ)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt


async def list_checked_in_meetings_for_employee(
    db: AsyncSession,
    employee_id: int,
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
) -> list[tuple[MeetingParticipant, str, datetime]]:
    """Lấy danh sách participant cuộc họp (kể cả chưa check-in) của nhân viên kèm tên cuộc họp và thời gian bắt đầu dự kiến."""
    query = (
        select(MeetingParticipant, Meeting.title, Meeting.scheduled_start)
        .join(Meeting, Meeting.id == MeetingParticipant.meeting_id)
        .where(MeetingParticipant.employee_id == employee_id)
        .order_by(Meeting.scheduled_start.asc())
    )
    if start_dt:
        query = query.where(Meeting.scheduled_start >= start_dt)
    if end_dt:
        query = query.where(Meeting.scheduled_start < end_dt)
        
    result = await db.execute(query)
    return list(result.all())


async def list_checked_in_events_for_employee(
    db: AsyncSession,
    employee_id: int,
    start_dt: datetime | None = None,
    end_dt: datetime | None = None,
) -> list[tuple[RecognitionLog, str]]:
    """Lấy danh sách log nhận diện đã xác nhận gắn với sự kiện của nhân viên kèm tên sự kiện."""
    query = (
        select(RecognitionLog, Event.title)
        .join(Event, Event.id == RecognitionLog.event_id)
        .where(
            RecognitionLog.employee_id == employee_id,
            RecognitionLog.final_label == RecognitionLabel.CONFIRMED,
        )
        .order_by(RecognitionLog.captured_at.asc())
    )
    if start_dt:
        query = query.where(RecognitionLog.captured_at >= start_dt)
    if end_dt:
        query = query.where(RecognitionLog.captured_at < end_dt)
        
    result = await db.execute(query)
    return list(result.all())
