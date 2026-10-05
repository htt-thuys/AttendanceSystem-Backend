from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.admin.schemas import RecognitionLogItemResponse
from modules.recognition_logs import service

router = APIRouter()


@router.get("/recognition-logs", response_model=list[RecognitionLogItemResponse])
async def get_recognition_logs(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    camera_id: int | None = None,
    event_id: int | None = None,
    meeting_id: int | None = None,
    employee_id: int | None = None,
    result_label: str | None = None,
    final_label: str | None = None,
    include_pending: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.list_recognition_logs(
        db=db,
        date_from=date_from,
        date_to=date_to,
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        employee_id=employee_id,
        result_label=result_label,
        final_label=final_label,
        include_pending=include_pending,
        limit=limit,
    )


@router.get("/recognition-logs/recent-public", response_model=list[RecognitionLogItemResponse])
async def get_recent_public_recognition_logs(
    camera_id: int | None = Query(default=None),
    event_id: int | None = Query(default=None),
    meeting_id: int | None = Query(default=None),
    default_event_only: bool = Query(default=False),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_recent_public_recognition_logs(
        db=db,
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        default_event_only=default_event_only,
        limit=limit,
    )
