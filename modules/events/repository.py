from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Employee, Event, RecognitionLog


async def create_event_record(
    db: AsyncSession,
    title: str,
    description: str | None,
    starts_at: datetime,
    ends_at: datetime,
    created_by: int,
) -> Event:
    event = Event(
        title=title,
        description=description,
        starts_at=starts_at,
        ends_at=ends_at,
        created_by=created_by,
        is_active=True,
    )
    db.add(event)
    await db.flush()
    return event


async def get_event_record(db: AsyncSession, event_id: int) -> Event | None:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def list_event_attendance_logs(
    db: AsyncSession,
    event_id: int,
) -> list[tuple[RecognitionLog, str | None, str | None]]:
    query = (
        select(RecognitionLog, Employee.full_name, Employee.employee_code)
        .outerjoin(Employee, Employee.id == RecognitionLog.employee_id)
        .where(
            RecognitionLog.event_id == event_id,
            (RecognitionLog.employee_id.is_(None)) | (Employee.status != "deleted"),
        )
        .order_by(RecognitionLog.captured_at.asc(), RecognitionLog.id.asc())
    )
    result = await db.execute(query)
    return list(result.all())


async def list_event_records(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
    now: datetime | None = None,
) -> list[Event]:
    query = select(Event).order_by(Event.starts_at.desc(), Event.id.desc())

    conditions = []
    if date_from:
        start_dt, _ = _build_day_range(date_from)
        conditions.append(Event.ends_at >= start_dt)
    if date_to:
        _, end_dt = _build_day_range(date_to)
        conditions.append(Event.starts_at < end_dt)
    if status:
        if now is None:
            now = datetime.now(tz=timezone.utc)
        if status == "active":
            conditions.append(Event.is_active.is_(True))
        elif status == "inactive":
            conditions.append(Event.is_active.is_(False))
        elif status == "running":
            conditions.extend([Event.is_active.is_(True), Event.starts_at <= now, Event.ends_at >= now])
        elif status == "upcoming":
            conditions.extend([Event.is_active.is_(True), Event.starts_at > now])
        elif status == "ended":
            conditions.extend([Event.is_active.is_(True), Event.ends_at < now])
        elif status == "all":
            pass
    else:
        conditions.append(Event.is_active.is_(True))
    if conditions:
        query = query.where(*conditions)
    if offset:
        query = query.offset(offset)
    if limit is not None:
        query = query.limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def list_upcoming_public_event_records(
    db: AsyncSession,
    now: datetime,
    lookahead_minutes: int,
    limit: int | None,
) -> list[Event]:
    visible_until = now + timedelta(minutes=lookahead_minutes)
    query = (
        select(Event)
        .where(
            Event.is_active.is_(True),
            Event.ends_at >= now,
            Event.starts_at <= visible_until,
        )
        .order_by(Event.starts_at.asc(), Event.id.asc())
    )
    if limit is not None:
        query = query.limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


def _build_day_range(target_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(target_date, time.min)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt
