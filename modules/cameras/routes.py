from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.cameras import service
from modules.cameras.schemas import (
    CameraCreateRequest,
    CameraDetailResponse,
    CameraResponse,
    CameraStatusUpdateRequest,
    CameraUpdateRequest,
)

router = APIRouter()


@router.get("/cameras", response_model=list[CameraDetailResponse])
async def list_cameras(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.list_cameras(db=db)


@router.post("/cameras", response_model=CameraResponse)
async def create_camera(
    payload: CameraCreateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.create_camera(db=db, payload=payload)


@router.patch("/cameras/{camera_id}", response_model=CameraResponse)
async def update_camera(
    camera_id: int,
    payload: CameraUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.update_camera(db=db, camera_id=camera_id, payload=payload)


@router.patch("/cameras/{camera_id}/status", response_model=CameraResponse)
async def update_camera_status(
    camera_id: int,
    payload: CameraStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.update_camera_status(db=db, camera_id=camera_id, payload=payload)
