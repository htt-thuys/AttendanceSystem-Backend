from datetime import date
import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user, require_roles
from infrastructure.database.models import User
from infrastructure.database.session import get_db
from modules.attendance import service
from modules.attendance.schemas import (
    AttendanceAbsenceRequest,
    AttendanceExportRequest,
    AttendanceListItemResponse,
    AttendanceReportResponse,
    AttendanceTodaySummaryResponse,
    AttendanceUpdateNoteRequest,
)

router = APIRouter()


@router.get("/attendance", response_model=list[AttendanceListItemResponse])
async def list_attendance(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    employee_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
):
    """Lấy danh sách bản ghi điểm danh."""
    return await service.list_attendance(
        db=db,
        date_from=date_from,
        date_to=date_to,
        employee_id=employee_id,
        status=status,
    )


@router.get("/attendance/today", response_model=AttendanceTodaySummaryResponse)
async def get_attendance_today(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
):
    """Lấy tổng hợp điểm danh ngày hôm nay."""
    return await service.get_today_summary(db=db)


@router.get("/attendance/report", response_model=AttendanceReportResponse)
async def get_attendance_report(
    date_from: date = Query(...),
    date_to: date = Query(...),
    employee_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
):
    """Lấy báo cáo điểm danh theo khoảng ngày."""
    return await service.get_report(
        db=db,
        date_from=date_from,
        date_to=date_to,
        employee_id=employee_id,
        status=status,
    )


@router.get("/me/attendance", response_model=list[AttendanceListItemResponse])
async def get_my_attendance(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nhân viên xem lịch sử điểm danh của mình."""
    return await service.list_my_attendance(
        db=db,
        current_user=current_user,
        date_from=date_from,
        date_to=date_to,
        status=status,
    )


@router.post("/attendance/export")
async def export_attendance(
    payload: AttendanceExportRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
):
    """Xuất dữ liệu điểm danh ra CSV."""
    export_format, records = await service.export_attendance(db=db, payload=payload)

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
    for record in records:
        writer.writerow(
            [
                record.id,
                record.employee_id,
                record.employee_name or "",
                record.date.isoformat(),
                record.check_in_time.isoformat() if record.check_in_time else "",
                record.check_out_time.isoformat() if record.check_out_time else "",
                record.status,
                record.work_hours if record.work_hours is not None else "",
                record.note or "",
            ]
        )

    content = buffer.getvalue()
    filename = f"attendance_export.{export_format}"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=content, media_type="text/csv", headers=headers)


@router.post("/me/attendance/absence-request", response_model=AttendanceListItemResponse)
async def request_absence(
    payload: AttendanceAbsenceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Nhân viên tự báo vắng có phép cho một ngày."""
    return await service.request_absence(
        db=db,
        current_user=current_user,
        target_date=payload.date,
        reason=payload.reason,
    )


@router.patch("/attendance/{record_id}", response_model=AttendanceListItemResponse)
async def admin_update_attendance(
    record_id: int,
    payload: AttendanceUpdateNoteRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_roles("admin")),
):
    """Admin cập nhật trạng thái hoặc ghi chú bản ghi điểm danh."""
    return await service.admin_update_attendance(
        db=db,
        record_id=record_id,
        status=payload.status,
        note=payload.note,
    )
