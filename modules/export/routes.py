from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.export import service
from modules.export.schemas import AttendanceExportRequest, EmployeesExportRequest, RecognitionLogsExportRequest

router = APIRouter()


@router.post("/export/attendance")
async def export_attendance(
    payload: AttendanceExportRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Xuất điểm danh ra CSV."""
    content = await service.export_attendance(db=db, payload=payload)
    headers = {"Content-Disposition": "attachment; filename=attendance_export.csv"}
    return Response(content=content, media_type="text/csv", headers=headers)


@router.post("/export/recognition-logs")
async def export_recognition_logs(
    payload: RecognitionLogsExportRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Xuất nhật ký nhận diện ra CSV."""
    content = await service.export_recognition_logs(db=db, payload=payload)
    headers = {"Content-Disposition": "attachment; filename=recognition_logs_export.csv"}
    return Response(content=content, media_type="text/csv", headers=headers)


@router.post("/export/employees")
async def export_employees(
    payload: EmployeesExportRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Xuất danh sách nhân viên ra CSV."""
    content = await service.export_employees(db=db, payload=payload)
    headers = {"Content-Disposition": "attachment; filename=employees_export.csv"}
    return Response(content=content, media_type="text/csv", headers=headers)
