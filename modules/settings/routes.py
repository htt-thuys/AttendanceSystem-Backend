from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.settings import service
from modules.admin.schemas import RuntimeSettingsResponse, RuntimeSettingsUpdateRequest

router = APIRouter()


@router.get("/settings", response_model=RuntimeSettingsResponse)
async def get_admin_settings(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.get_admin_settings(db=db)


@router.patch("/settings", response_model=RuntimeSettingsResponse)
async def update_admin_settings(
    payload: RuntimeSettingsUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.update_admin_settings(db=db, payload=payload)


@router.post("/settings/reset", response_model=RuntimeSettingsResponse)
async def reset_admin_settings(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.reset_admin_settings(db=db)
