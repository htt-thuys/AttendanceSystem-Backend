from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.dashboard import service
from modules.dashboard.schemas import (
    AttendanceTrendResponse,
    CameraStatusResponse,
    DashboardStatsResponse,
    LateArrivalsResponse,
    RecognitionActivityResponse,
)

router = APIRouter()


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Lấy thống kê tổng quan dashboard."""
    return await service.get_dashboard_stats(db=db)


@router.get("/dashboard/attendance-trend", response_model=AttendanceTrendResponse)
async def get_attendance_trend(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Lấy xu hướng điểm danh."""
    return await service.get_attendance_trend(db=db, date_from=date_from, date_to=date_to)


@router.get("/dashboard/recognition-activity", response_model=RecognitionActivityResponse)
async def get_recognition_activity(
    date_from: date = Query(...),
    date_to: date = Query(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Lấy hoạt động nhận diện theo thời gian."""
    return await service.get_recognition_activity(db=db, date_from=date_from, date_to=date_to)


@router.get("/dashboard/late-arrivals", response_model=LateArrivalsResponse)
async def get_late_arrivals(
    target_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Lấy danh sách đi trễ hôm nay."""
    if target_date is None:
        target_date = date.today()
    return await service.get_late_arrivals(db=db, target_date=target_date)


@router.get("/dashboard/camera-status", response_model=CameraStatusResponse)
async def get_camera_status(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    """Lấy trạng thái camera."""
    return await service.get_camera_status(db=db)
