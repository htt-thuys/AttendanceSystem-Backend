from datetime import date, datetime, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Employee, Event, Meeting, RecognitionLog


async def list_recognition_logs(
    db: AsyncSession,
    date_value: date | None = None,
    camera_id: int | None = None,
    event_id: int | None = None,
    meeting_id: int | None = None,
    default_event_only: bool = False,
    employee_id: int | None = None,
    result_label: str | None = None,
    final_label: str | None = None,
    include_pending: bool = True,
    public_visible_only: bool = False,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
) -> list[tuple[RecognitionLog, str | None, str | None, str | None]]:
    query = (
        select(RecognitionLog, Employee.full_name, Event.title, Meeting.title)
        .outerjoin(Employee, Employee.id == RecognitionLog.employee_id)
        .outerjoin(Event, Event.id == RecognitionLog.event_id)
        .outerjoin(Meeting, Meeting.id == RecognitionLog.meeting_id)
        .where(or_(RecognitionLog.employee_id.is_(None), Employee.status != "deleted"))
        .order_by(RecognitionLog.captured_at.desc(), RecognitionLog.id.desc())
        .limit(limit)
    )

    conditions = []
    if date_value:
        start_dt, end_dt = _build_day_range(date_value)
        conditions.extend([RecognitionLog.captured_at >= start_dt, RecognitionLog.captured_at < end_dt])
    if date_from:
        start_dt, _ = _build_day_range(date_from)
        conditions.append(RecognitionLog.captured_at >= start_dt)
    if date_to:
        _, end_dt = _build_day_range(date_to)
        conditions.append(RecognitionLog.captured_at < end_dt)
    if camera_id is not None:
        conditions.append(RecognitionLog.camera_id == camera_id)
    if event_id is not None:
        conditions.append(RecognitionLog.event_id == event_id)
    if meeting_id is not None:
        conditions.append(RecognitionLog.meeting_id == meeting_id)
    elif default_event_only:
        conditions.append(RecognitionLog.event_id.is_(None))
        conditions.append(RecognitionLog.meeting_id.is_(None))
    if employee_id is not None:
        conditions.append(RecognitionLog.employee_id == employee_id)
    if result_label:
        conditions.append(RecognitionLog.result_label == result_label)
    if final_label:
        conditions.append(RecognitionLog.final_label == final_label)
    if not include_pending:
        conditions.append(
            or_(
                RecognitionLog.final_label.is_not(None),
                RecognitionLog.result_label == "unknown",
            )
        )
    if public_visible_only:
        conditions.append(
            or_(
                RecognitionLog.final_label == "confirmed",
                RecognitionLog.result_label == "unknown",
            )
        )

    if conditions:
        query = query.where(*conditions)

    result = await db.execute(query)
    return list(result.all())


def _build_day_range(target_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(target_date, time.min)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt
