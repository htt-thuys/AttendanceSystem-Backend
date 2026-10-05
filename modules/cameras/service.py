from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Camera
from modules.cameras import repository
from modules.cameras.schemas import (
    CameraCreateRequest,
    CameraDetailResponse,
    CameraResponse,
    CameraStatusUpdateRequest,
    CameraUpdateRequest,
)


async def list_cameras(db: AsyncSession) -> list[CameraDetailResponse]:
    rows = await repository.list_camera_records(db)
    return [
        CameraDetailResponse(
            id=camera.id,
            location=camera.location,
            is_active=camera.is_active,
            last_seen_at=last_seen_at,
        )
        for camera, last_seen_at in rows
    ]


async def create_camera(db: AsyncSession, payload: CameraCreateRequest) -> CameraResponse:
    camera = await repository.create_camera_record(
        db=db,
        location=_normalize_text(payload.location),
        is_active=payload.is_active,
    )
    await db.commit()
    await db.refresh(camera)
    return _build_camera_response(camera)


async def update_camera(
    db: AsyncSession,
    camera_id: int,
    payload: CameraUpdateRequest,
) -> CameraResponse:
    camera = await _get_camera_or_404(db=db, camera_id=camera_id)
    if "location" in payload.model_fields_set:
        camera.location = _normalize_text(payload.location)
    await db.commit()
    await db.refresh(camera)
    return _build_camera_response(camera)


async def update_camera_status(
    db: AsyncSession,
    camera_id: int,
    payload: CameraStatusUpdateRequest,
) -> CameraResponse:
    camera = await _get_camera_or_404(db=db, camera_id=camera_id)
    camera.is_active = payload.is_active
    await db.commit()
    await db.refresh(camera)
    return _build_camera_response(camera)


async def ensure_active_camera(db: AsyncSession, camera_id: int) -> Camera:
    camera = await _get_camera_or_404(db=db, camera_id=camera_id)
    if not camera.is_active:
        raise HTTPException(status_code=400, detail="Camera dang bi vo hieu hoa")
    return camera


async def _get_camera_or_404(db: AsyncSession, camera_id: int) -> Camera:
    camera = await repository.get_camera_record(db=db, camera_id=camera_id)
    if not camera:
        raise HTTPException(status_code=400, detail="Khong tim thay camera")
    return camera


def _build_camera_response(camera: Camera) -> CameraResponse:
    return CameraResponse(id=camera.id, location=camera.location, is_active=camera.is_active)


def _normalize_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
