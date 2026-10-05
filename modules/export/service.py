from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import AttendanceRecord, Employee, Event, RecognitionLog
from modules.export.schemas import AttendanceExportRequest, EmployeesExportRequest, RecognitionLogsExportRequest


async def export_attendance(db: AsyncSession, payload: AttendanceExportRequest) -> str:
    """Xuất dữ liệu điểm danh ra CSV."""
    _ensure_csv(payload.format)

    query = (
        select(AttendanceRecord, Employee.full_name)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .where(Employee.status != "deleted")
        .order_by(AttendanceRecord.date.desc(), AttendanceRecord.id.desc())
    )

    conditions = []
    if payload.date_from:
        conditions.append(AttendanceRecord.date >= payload.date_from)
    if payload.date_to:
        conditions.append(AttendanceRecord.date <= payload.date_to)
    if payload.employee_id is not None:
        conditions.append(AttendanceRecord.employee_id == payload.employee_id)
    if payload.status:
        conditions.append(AttendanceRecord.status == payload.status)
    if conditions:
        query = query.where(*conditions)

    result = await db.execute(query)
    rows = list(result.all())

    header = [
        "id",
        "employee_id",
        "employee_name",
        "date",
        "check_in_time",
        "check_out_time",
        "status",
        "work_hours",
        "note",
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for record, employee_name in rows:
        writer.writerow(
            [
                record.id,
                record.employee_id,
                employee_name or "",
                record.date.isoformat(),
                record.check_in_time.isoformat() if record.check_in_time else "",
                record.check_out_time.isoformat() if record.check_out_time else "",
                record.status,
                record.work_hours if record.work_hours is not None else "",
                record.note or "",
            ]
        )
    return buffer.getvalue()


async def export_recognition_logs(db: AsyncSession, payload: RecognitionLogsExportRequest) -> str:
    """Xuất nhật ký nhận diện ra CSV."""
    _ensure_csv(payload.format)

    query = (
        select(RecognitionLog, Employee.full_name, Event.title)
        .outerjoin(Employee, Employee.id == RecognitionLog.employee_id)
        .outerjoin(Event, Event.id == RecognitionLog.event_id)
        .where(or_(RecognitionLog.employee_id.is_(None), Employee.status != "deleted"))
        .order_by(RecognitionLog.captured_at.desc(), RecognitionLog.id.desc())
    )

    conditions = []
    if payload.date_from:
        start_dt, _ = _build_day_range(payload.date_from)
        conditions.append(RecognitionLog.captured_at >= start_dt)
    if payload.date_to:
        _, end_dt = _build_day_range(payload.date_to)
        conditions.append(RecognitionLog.captured_at < end_dt)
    if payload.employee_id is not None:
        conditions.append(RecognitionLog.employee_id == payload.employee_id)
    if payload.camera_id is not None:
        conditions.append(RecognitionLog.camera_id == payload.camera_id)
    if payload.event_id is not None:
        conditions.append(RecognitionLog.event_id == payload.event_id)
    if payload.result_label:
        conditions.append(RecognitionLog.result_label == payload.result_label)
    if payload.final_label:
        conditions.append(RecognitionLog.final_label == payload.final_label)
    if conditions:
        query = query.where(*conditions)

    result = await db.execute(query)
    rows = list(result.all())

    header = [
        "id",
        "captured_at",
        "camera_id",
        "event_id",
        "event_title",
        "employee_id",
        "employee_name",
        "result_label",
        "final_label",
        "top_score",
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for record, employee_name, event_title in rows:
        writer.writerow(
            [
                record.id,
                record.captured_at.isoformat() if record.captured_at else "",
                record.camera_id or "",
                record.event_id or "",
                event_title or "",
                record.employee_id or "",
                employee_name or "",
                record.result_label or "",
                record.final_label or "",
                record.top_score if record.top_score is not None else "",
            ]
        )
    return buffer.getvalue()


async def export_employees(db: AsyncSession, payload: EmployeesExportRequest) -> str:
    """Xuất danh sách nhân viên ra CSV."""
    _ensure_csv(payload.format)

    query = select(Employee).where(Employee.status != "deleted").order_by(Employee.id.asc())
    if payload.status:
        query = query.where(Employee.status == payload.status)
    result = await db.execute(query)
    rows = list(result.scalars().all())

    header = [
        "id",
        "full_name",
        "employee_code",
        "status",
        "created_at",
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header)
    for employee in rows:
        writer.writerow(
            [
                employee.id,
                employee.full_name,
                employee.employee_code,
                employee.status,
                employee.created_at.isoformat() if employee.created_at else "",
            ]
        )
    return buffer.getvalue()


def _ensure_csv(format_value: str) -> None:
    """Chỉ cho phép export CSV."""
    if format_value.lower() != "csv":
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ export định dạng CSV")


def _build_day_range(target_date: date) -> tuple[datetime, datetime]:
    """Tạo khoảng thời gian [start, end) cho một ngày."""
    start_dt = datetime.combine(target_date, time.min)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt
