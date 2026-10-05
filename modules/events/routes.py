from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.models import User
from infrastructure.database.session import get_db
from modules.events import service
from modules.events.schemas import (
    EventAttendanceResponse,
    EventBasicResponse,
    EventCreateRequest,
    EventResponse,
    EventUpdateRequest,
)

router = APIRouter()


@router.get("/events/list-public", response_model=list[EventBasicResponse])
async def list_active_public_events(
    limit: int | None = Query(default=None, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_active_public_events(db=db, limit=limit)


@router.get("/events/upcoming-public", response_model=list[EventBasicResponse])
async def list_upcoming_public_events(
    limit: int | None = Query(default=None, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await service.list_upcoming_public_events(db=db, limit=limit)


@router.get("/events", response_model=list[EventResponse])
async def list_events(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.list_events(
        db=db,
        date_from=date_from,
        date_to=date_to,
        status=status,
        limit=limit,
        offset=offset,
    )


@router.post("/events", response_model=EventResponse)
async def create_event(
    payload: EventCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    return await service.create_event(db=db, payload=payload, current_user=current_user)


@router.get("/events/{event_id:int}", response_model=EventResponse)
async def get_event_detail(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.get_event_detail(db=db, event_id=event_id)


@router.get("/events/{event_id:int}/attendance", response_model=EventAttendanceResponse)
async def get_event_attendance(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.get_event_attendance(db=db, event_id=event_id)


@router.patch("/events/{event_id:int}", response_model=EventResponse)
async def update_event(
    event_id: int,
    payload: EventUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.update_event(db=db, event_id=event_id, payload=payload)


@router.delete("/events/{event_id:int}", response_model=EventResponse)
async def deactivate_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.deactivate_event(db=db, event_id=event_id)
