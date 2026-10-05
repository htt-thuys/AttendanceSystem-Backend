from datetime import date, datetime, time, timedelta

from sqlalchemy import delete, func, select, update, or_
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Camera, Employee, Meeting, MeetingParticipant, Notification, User
from modules.meetings.enums import MeetingStatus, ParticipantStatus

EARLY_CHECKIN_WINDOW = timedelta(minutes=30)
POST_END_MATCH_WINDOW = timedelta(days=1)

async def get_meeting_record(db: AsyncSession, meeting_id: int) -> Meeting | None:
    query = select(Meeting).where(Meeting.id == meeting_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def list_meeting_records(
    db: AsyncSession,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
) -> list[tuple[Meeting, int]]:
    query = (
        select(Meeting, func.count(MeetingParticipant.id))
        .outerjoin(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .group_by(Meeting.id)
        .order_by(Meeting.scheduled_start.desc(), Meeting.id.desc())
    )

    conditions = []
    if date_from:
        start_dt, _ = _build_day_range(date_from)
        conditions.append(Meeting.scheduled_start >= start_dt)
    if date_to:
        _, end_dt = _build_day_range(date_to)
        conditions.append(Meeting.scheduled_start < end_dt)
    if status:
        conditions.append(Meeting.status == status)
    if conditions:
        query = query.where(*conditions)

    result = await db.execute(query)
    return list(result.all())

async def list_meeting_participants(
    db: AsyncSession,
    meeting_id: int,
) -> list[tuple[MeetingParticipant, str | None]]:
    query = (
        select(MeetingParticipant, Employee.full_name)
        .join(Employee, Employee.id == MeetingParticipant.employee_id)
        .where(MeetingParticipant.meeting_id == meeting_id)
        .order_by(MeetingParticipant.id.asc())
    )
    result = await db.execute(query)
    return list(result.all())


async def get_meeting_participant(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
) -> MeetingParticipant | None:
    query = select(MeetingParticipant).where(
        MeetingParticipant.meeting_id == meeting_id,
        MeetingParticipant.employee_id == employee_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def create_meeting_record(
    db: AsyncSession,
    title: str,
    description: str | None,
    scheduled_start: datetime,
    scheduled_end: datetime | None,
    location: str | None,
    camera_id: int | None,
    created_by: int,
) -> Meeting:
    meeting = Meeting(
        title=title,
        description=description,
        scheduled_start=scheduled_start,
        scheduled_end=scheduled_end,
        location=location,
        camera_id=camera_id,
        created_by=created_by,
        status=MeetingStatus.SCHEDULED,
    )
    db.add(meeting)
    await db.flush()
    return meeting

async def create_meeting_participants(
    db: AsyncSession,
    meeting_id: int,
    employee_ids: list[int],
) -> list[MeetingParticipant]:
    participants: list[MeetingParticipant] = []
    for employee_id in employee_ids:
        participant = MeetingParticipant(
            meeting_id=meeting_id,
            employee_id=employee_id,
            status=ParticipantStatus.INVITED,
        )
        db.add(participant)
        participants.append(participant)
    await db.flush()
    return participants

async def delete_meeting_participant(
    db: AsyncSession,
    meeting_id: int,
    employee_id: int,
) -> None:
    await db.execute(
        delete(MeetingParticipant).where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.employee_id == employee_id,
        )
    )

async def list_existing_employee_ids(
    db: AsyncSession,
    employee_ids: list[int],
) -> set[int]:
    if not employee_ids:
        return set()
    query = select(Employee.id).where(
        Employee.id.in_(employee_ids),
        Employee.status != "deleted",  # Employee status not in meetings enums scope
    )
    result = await db.execute(query)
    return {row[0] for row in result.all()}

async def list_users_by_employee_ids(db: AsyncSession, employee_ids: list[int]) -> list[User]:
    """Lấy danh sách user đang hoạt động theo danh sách employee_id."""
    if not employee_ids:
        return []
    query = select(User).where(
        User.employee_id.in_(employee_ids),
        User.is_active == True,
    )
    result = await db.execute(query)
    return list(result.scalars().all())

async def get_camera_record(db: AsyncSession, camera_id: int) -> Camera | None:
    query = select(Camera).where(Camera.id == camera_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()

async def update_participant_checkin(
    db: AsyncSession,
    participant: MeetingParticipant,
    check_in_time: datetime,
    check_in_log_id: int | None = None,
    note: str | None = None,
    status: str = "present",
) -> MeetingParticipant:
    """Cập nhật check-in cho người tham gia cuộc họp."""
    participant.status = status
    participant.check_in_time = check_in_time
    participant.check_in_log_id = check_in_log_id
    if note is not None:
        participant.note = note
    await db.flush()
    return participant


async def update_participant_status(
    db: AsyncSession,
    participant: MeetingParticipant,
    status: str,
    note: str | None = None,
) -> MeetingParticipant:
    """Cập nhật trạng thái participant mà không ghi nhận thời điểm check-in."""
    participant.status = status
    if note is not None:
        participant.note = note
    await db.flush()
    return participant

async def update_participant_checkout(
    db: AsyncSession,
    participant: MeetingParticipant,
    check_out_time: datetime,
    check_out_log_id: int | None = None,
    note: str | None = None,
) -> MeetingParticipant:
    """Cập nhật check-out cho người tham gia cuộc họp."""
    participant.check_out_time = check_out_time
    participant.check_out_log_id = check_out_log_id
    if note is not None:
        participant.note = note
    await db.flush()
    return participant

async def list_active_meetings_by_camera(
    db: AsyncSession,
    camera_id: int,
    captured_at: datetime,
) -> list[Meeting]:
    """Lay meeting theo camera co the cap nhat attendance tai thoi diem capture."""
    query = select(Meeting).where(
        Meeting.camera_id == camera_id,
        Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS, MeetingStatus.COMPLETED]),
        Meeting.scheduled_start <= captured_at + EARLY_CHECKIN_WINDOW,
        Meeting.scheduled_end.is_not(None),
        Meeting.scheduled_end >= captured_at - POST_END_MATCH_WINDOW,
    )
    result = await db.execute(query)
    return list(result.scalars().all())

async def list_candidate_meetings_for_employee_seen_at(
    db: AsyncSession,
    employee_id: int,
    seen_at: datetime,
    camera_id: int | None = None,
) -> list[Meeting]:
    """Tìm các meeting có employee trong danh sách theo thời điểm unknown first_seen_at."""
    query = (
        select(Meeting)
        .join(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .where(
            MeetingParticipant.employee_id == employee_id,
            Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS, MeetingStatus.COMPLETED]),
            Meeting.scheduled_start <= seen_at + EARLY_CHECKIN_WINDOW,
            Meeting.scheduled_end.is_not(None),
            Meeting.scheduled_end >= seen_at - POST_END_MATCH_WINDOW,
        )
    )
    if camera_id is not None:
        query = query.where(Meeting.camera_id == camera_id)
    result = await db.execute(query)
    return list(result.scalars().all())

async def mark_unchecked_participants_absent(
    db: AsyncSession,
    meeting_id: int,
) -> int:
    """Đánh dấu các participant chưa check-in của meeting là absent."""
    result = await db.execute(
        update(MeetingParticipant)
        .where(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.check_in_time.is_(None),
            MeetingParticipant.status == ParticipantStatus.INVITED,
        )
        .values(status=ParticipantStatus.ABSENT)
    )
    return int(result.rowcount or 0)

async def create_notifications(
    db: AsyncSession,
    user_ids: list[int],
    type_: str,
    title: str,
    message: str | None,
    data: dict | None = None,
) -> None:
    """Tạo notification nội bộ cho danh sách user."""
    for user_id in user_ids:
        db.add(
            Notification(
                user_id=user_id,
                type=type_,
                title=title,
                message=message,
                data=data,
            )
        )
    await db.flush()


async def list_active_public_meeting_records(
    db: AsyncSession,
    now: datetime,
) -> list[tuple[Meeting, int]]:
    """Lấy danh sách các cuộc họp đang hoạt động (in_progress) hoặc sắp bắt đầu (scheduled) công khai."""
    query = (
        select(Meeting, func.count(MeetingParticipant.id))
        .outerjoin(MeetingParticipant, MeetingParticipant.meeting_id == Meeting.id)
        .group_by(Meeting.id)
        .where(
            Meeting.status.in_([MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS]),
            or_(Meeting.scheduled_end.is_(None), Meeting.scheduled_end >= now)
        )
        .order_by(Meeting.scheduled_start.asc(), Meeting.id.asc())
    )
    result = await db.execute(query)
    return list(result.all())


def _build_day_range(target_date: date) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(target_date, time.min)
    end_dt = start_dt + timedelta(days=1)
    return start_dt, end_dt

