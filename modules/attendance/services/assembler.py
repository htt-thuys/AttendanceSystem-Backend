"""Assembler helpers for attendance response composition."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from modules.attendance import repository
from modules.attendance.helpers import LOCAL_TZ, build_attendance_item
from modules.attendance.schemas import (
    AttendanceEventInfo,
    AttendanceListItemResponse,
    AttendanceMeetingInfo,
)


def build_meetings_by_date(meetings_rows) -> dict[date, list[AttendanceMeetingInfo]]:
    """Group meeting participant rows by local date."""
    meetings_by_date: dict[date, list[AttendanceMeetingInfo]] = defaultdict(list)
    for participant, meeting_title, scheduled_start in meetings_rows:
        local_dt = (
            scheduled_start.astimezone(LOCAL_TZ)
            if scheduled_start.tzinfo
            else scheduled_start
        )
        meetings_by_date[local_dt.date()].append(
            AttendanceMeetingInfo(
                id=participant.meeting_id,
                title=meeting_title,
                check_in_time=participant.check_in_time,
                check_out_time=participant.check_out_time,
                status=participant.status,
            )
        )
    return meetings_by_date


def build_events_by_date(events_rows) -> dict[date, list[AttendanceEventInfo]]:
    """Group event recognition rows by local date."""
    events_by_date: dict[date, list[AttendanceEventInfo]] = defaultdict(list)
    for log, event_title in events_rows:
        local_dt = (
            log.captured_at.astimezone(LOCAL_TZ)
            if log.captured_at.tzinfo
            else log.captured_at
        )
        events_by_date[local_dt.date()].append(
            AttendanceEventInfo(
                id=log.event_id,
                title=event_title,
                check_in_time=log.captured_at,
            )
        )
    return events_by_date


def attach_daily_context(
    rows: list[tuple],
    meetings_by_date: dict[date, list[AttendanceMeetingInfo]],
    events_by_date: dict[date, list[AttendanceEventInfo]],
) -> list[AttendanceListItemResponse]:
    """Attach meetings/events into attendance list items."""
    return [
        build_attendance_item(
            record,
            employee_name,
            meetings=meetings_by_date.get(record.date, []),
            events=events_by_date.get(record.date, []),
        )
        for record, employee_name in rows
    ]


async def build_my_attendance_items(
    db: AsyncSession,
    employee_id: int,
    rows: list[tuple],
    date_from: date | None,
    date_to: date | None,
) -> list[AttendanceListItemResponse]:
    """Build attendance items for current user with meetings/events context."""
    start_dt: datetime | None = None
    if date_from:
        start_dt, _ = repository._build_day_range(date_from)

    end_dt: datetime | None = None
    if date_to:
        _, end_dt = repository._build_day_range(date_to)

    meetings_rows = await repository.list_checked_in_meetings_for_employee(
        db=db,
        employee_id=employee_id,
        start_dt=start_dt,
        end_dt=end_dt,
    )
    events_rows = await repository.list_checked_in_events_for_employee(
        db=db,
        employee_id=employee_id,
        start_dt=start_dt,
        end_dt=end_dt,
    )

    meetings_by_date = build_meetings_by_date(meetings_rows)
    events_by_date = build_events_by_date(events_rows)
    return attach_daily_context(rows, meetings_by_date, events_by_date)
