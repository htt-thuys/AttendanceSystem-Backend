from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import RecognitionLog


async def find_recent_employee_log(
    db: AsyncSession,
    employee_id: int,
    camera_id: int | None,
    cooldown_minutes: int,
) -> RecognitionLog | None:
    """Find a recent recognition log for the same employee and camera."""
    if cooldown_minutes <= 0:
        return None

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=cooldown_minutes)
    query = (
        select(RecognitionLog)
        .where(
            RecognitionLog.employee_id == employee_id,
            RecognitionLog.final_label == "confirmed",
            RecognitionLog.captured_at >= cutoff,
        )
        .order_by(RecognitionLog.captured_at.desc(), RecognitionLog.id.desc())
        .limit(1)
    )
    if camera_id is None:
        query = query.where(RecognitionLog.camera_id.is_(None))
    else:
        query = query.where(RecognitionLog.camera_id == camera_id)

    result = await db.execute(query)
    return result.scalar_one_or_none()
