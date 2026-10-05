from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.admin.schemas import AdminActionResponse, UnknownQueueItemResponse
from modules.unknown_queue import service

router = APIRouter()


class AssignRequest(BaseModel):
    """Schema body dung khi gan unknown queue cho mot nhan vien da co."""

    employee_id: int


@router.get("/unknown-queue", response_model=list[UnknownQueueItemResponse])
async def get_unknown_queue(
    event_id: int | None = Query(default=None),
    meeting_id: int | None = Query(default=None),
    event_scope: str | None = Query(default=None),
    default_event_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.list_unknown_queue(
        db=db,
        event_id=event_id,
        meeting_id=meeting_id,
        event_scope=event_scope,
        default_event_only=default_event_only,
    )


@router.post("/unknown-queue/{queue_id}/assign", response_model=AdminActionResponse)
async def assign_unknown(
    queue_id: int,
    req: AssignRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    await service.assign_unknown_queue(
        db=db,
        queue_id=queue_id,
        employee_id=req.employee_id,
    )
    return AdminActionResponse(success=True)


@router.post("/unknown-queue/{queue_id}/create", response_model=AdminActionResponse)
async def create_employee_from_unknown(
    queue_id: int,
    full_name: str = Form(...),
    employee_code: str = Form(...),
    avatar: UploadFile | None = File(None),
    vector_images: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    success, employee_id = await service.create_employee_from_unknown_queue(
        db=db,
        queue_id=queue_id,
        full_name=full_name,
        employee_code=employee_code,
        avatar=avatar,
        vector_images=vector_images,
    )
    return AdminActionResponse(success=success, employee_id=employee_id)


@router.post("/unknown-queue/{queue_id}/reject", response_model=AdminActionResponse)
async def reject_unknown(
    queue_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    await service.reject_unknown_queue(db=db, queue_id=queue_id)
    return AdminActionResponse(success=True)
