"""Mutation/action services for attendance."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User
from modules.attendance import repository
from modules.attendance.helpers import build_attendance_item, validate_status
from modules.attendance.schemas import AttendanceListItemResponse


async def request_absence(
    db: AsyncSession,
    current_user: User,
    target_date: date,
    reason: str,
) -> AttendanceListItemResponse:
    """Nhân viên tự báo vắng có phép cho một ngày cụ thể."""
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="Tài khoản chưa gắn với nhân viên")

    employee_id = current_user.employee_id
    today = date.today()
    if target_date < today:
        raise HTTPException(status_code=400, detail="Không thể báo vắng cho ngày đã qua")

    record = await repository.get_attendance_record(db, employee_id, target_date)
    if record:
        if record.check_in_time is not None:
            raise HTTPException(
                status_code=400,
                detail="Đã check-in trong ngày này, không thể báo vắng",
            )
        if record.status == "excused":
            raise HTTPException(
                status_code=400,
                detail="Đã báo vắng có phép cho ngày này rồi",
            )
        record.status = "excused"
        record.note = reason
    else:
        record = await repository.create_attendance_record(
            db=db,
            employee_id=employee_id,
            target_date=target_date,
            check_in_time=None,
            check_out_time=None,
            check_in_log_id=None,
            check_out_log_id=None,
            status="excused",
            work_hours=None,
            note=reason,
        )

    await db.commit()
    await db.refresh(record)

    employee = await repository.get_employee_by_id(db, employee_id)
    return build_attendance_item(record, employee.full_name if employee else None)


async def admin_update_attendance(
    db: AsyncSession,
    record_id: int,
    status: str | None = None,
    note: str | None = None,
) -> AttendanceListItemResponse:
    """Admin cập nhật trạng thái hoặc ghi chú cho bản ghi điểm danh."""
    if status:
        validate_status(status)

    record = await repository.get_attendance_record_by_id(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Không tìm thấy bản ghi điểm danh")

    if status is not None:
        record.status = status
    if note is not None:
        record.note = note

    await db.commit()
    await db.refresh(record)

    employee = await repository.get_employee_by_id(db, record.employee_id)
    return build_attendance_item(record, employee.full_name if employee else None)
