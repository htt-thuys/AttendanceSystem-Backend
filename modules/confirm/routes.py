from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.session import get_db
from modules.confirm import service
from modules.confirm.schemas import ConfirmRequest, ConfirmResponse

router = APIRouter()


@router.post("/recognition/confirm", response_model=ConfirmResponse)
async def confirm_recognition(
    req: ConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    return await service.confirm_recognition(db=db, req=req)
