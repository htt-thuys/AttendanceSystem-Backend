"""Query/report services for attendance."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import User
from modules.attendance import repository
from modules.attendance.helpers import build_attendance_item, build_stats, validate_status
from modules.attendance.schemas import (
    AttendanceExportRequest,
    AttendanceListItemResponse,
    AttendanceReportResponse,
    AttendanceTodaySummaryResponse,
)
from modules.attendance.services.assembler import build_my_attendance_items
from modules.attendance.services.sync_service import ensure_attendance_records


async def list_attendance(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
    employee_id: int | None = None,
    status: str | None = None,
) -> list[AttendanceListItemResponse]:
    """Lấy danh sách điểm danh theo bộ lọc."""
    validate_status(status)
    await ensure_attendance_records(db, date_from, date_to, employee_id)
    rows = await repository.list_attendance_records(
        db=db,
        date_from=date_from,
        date_to=date_to,
        employee_id=employee_id,
        status=status,
    )
    return [build_attendance_item(record, name) for record, name in rows]


async def get_today_summary(db: AsyncSession) -> AttendanceTodaySummaryResponse:
    """Tổng hợp điểm danh cho ngày hiện tại."""
    today = date.today()
    await ensure_attendance_records(db, today, today, None)
    rows = await repository.list_attendance_records(
        db=db,
        date_from=today,
        date_to=today,
    )
    return AttendanceTodaySummaryResponse(date=today, stats=build_stats(rows))


async def get_report(
    db: AsyncSession,
    date_from: date,
    date_to: date,
    employee_id: int | None = None,
    status: str | None = None,
) -> AttendanceReportResponse:
    """Lấy báo cáo điểm danh theo khoảng ngày."""
    validate_status(status)
    if date_from > date_to:
        raise HTTPException(
            status_code=400,
            detail="Ngày bắt đầu phải trước hoặc bằng ngày kết thúc",
        )

    await ensure_attendance_records(db, date_from, date_to, employee_id)
    rows = await repository.list_attendance_records(
        db=db,
        date_from=date_from,
        date_to=date_to,
        employee_id=employee_id,
        status=status,
    )
    return AttendanceReportResponse(
        date_from=date_from,
        date_to=date_to,
        stats=build_stats(rows),
        records=[build_attendance_item(record, name) for record, name in rows],
    )


async def list_my_attendance(
    db: AsyncSession,
    current_user: User,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
) -> list[AttendanceListItemResponse]:
    """Lấy lịch sử điểm danh của nhân viên đang đăng nhập."""
    validate_status(status)
    if not current_user.employee_id:
        raise HTTPException(status_code=400, detail="Tài khoản chưa gắn với nhân viên")

    await ensure_attendance_records(db, date_from, date_to, current_user.employee_id)
    rows = await repository.list_attendance_records(
        db=db,
        date_from=date_from,
        date_to=date_to,
        employee_id=current_user.employee_id,
        status=status,
    )
    return await build_my_attendance_items(
        db=db,
        employee_id=current_user.employee_id,
        rows=rows,
        date_from=date_from,
        date_to=date_to,
    )


async def export_attendance(
    db: AsyncSession,
    payload: AttendanceExportRequest,
) -> tuple[str, list[AttendanceListItemResponse]]:
    """Chuẩn bị dữ liệu export điểm danh theo bộ lọc."""
    validate_status(payload.status)
    export_format = payload.format.lower()
    if export_format != "csv":
        raise HTTPException(status_code=400, detail="Chỉ hỗ trợ export định dạng CSV")

    await ensure_attendance_records(
        db,
        payload.date_from,
        payload.date_to,
        payload.employee_id,
    )
    rows = await repository.list_attendance_records(
        db=db,
        date_from=payload.date_from,
        date_to=payload.date_to,
        employee_id=payload.employee_id,
        status=payload.status,
    )
    records = [build_attendance_item(record, name) for record, name in rows]
    return export_format, records
