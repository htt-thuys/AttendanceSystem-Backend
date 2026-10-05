from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Event, Meeting, UnknownQueue


async def list_unknown_queue_records(
    db: AsyncSession,
    event_id: int | None = None,
    meeting_id: int | None = None,
    event_scope: str | None = None,
) -> list[tuple[UnknownQueue, str | None, str | None]]:
    query = (
        select(UnknownQueue, Event.title, Meeting.title)
        .outerjoin(Event, Event.id == UnknownQueue.event_id)
        .outerjoin(Meeting, Meeting.id == UnknownQueue.meeting_id)
        .where(UnknownQueue.resolved_at.is_(None))
        .order_by(UnknownQueue.last_seen_at.desc())
    )
    if event_id is not None:
        query = query.where(UnknownQueue.event_id == event_id)
    if meeting_id is not None:
        query = query.where(UnknownQueue.meeting_id == meeting_id)
    elif event_scope == "default":
        query = query.where(UnknownQueue.event_id.is_(None), UnknownQueue.meeting_id.is_(None))
    elif event_scope == "inactive":
        query = query.where(UnknownQueue.event_id.is_not(None), Event.is_active.is_(False))
    result = await db.execute(query)
    return list(result.all())


async def get_unknown_queue_record(db: AsyncSession, queue_id: int) -> UnknownQueue | None:
    query = select(UnknownQueue).where(
        UnknownQueue.id == queue_id,
        UnknownQueue.resolved_at.is_(None),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()
