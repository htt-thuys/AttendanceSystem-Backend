from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Camera, RecognitionLog


async def list_camera_records(db: AsyncSession) -> list[tuple[Camera, datetime | None]]:
    latest_log_subquery = (
        select(RecognitionLog.camera_id, func.max(RecognitionLog.captured_at).label("last_seen_at"))
        .where(RecognitionLog.camera_id.is_not(None))
        .group_by(RecognitionLog.camera_id)
        .subquery()
    )
    query = (
        select(Camera, latest_log_subquery.c.last_seen_at)
        .outerjoin(latest_log_subquery, latest_log_subquery.c.camera_id == Camera.id)
        .order_by(Camera.id.asc())
    )
    result = await db.execute(query)
    return list(result.all())


async def get_camera_record(db: AsyncSession, camera_id: int) -> Camera | None:
    query = select(Camera).where(Camera.id == camera_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_camera_record(
    db: AsyncSession,
    location: str | None,
    is_active: bool,
) -> Camera:
    camera = Camera(location=location, is_active=is_active)
    db.add(camera)
    await db.flush()
    return camera
