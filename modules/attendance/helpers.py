"""Pure helper functions for the attendance module (no DB access)."""

from collections import Counter
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException

from infrastructure.database.models import WorkSchedule
from modules.attendance.enums import (
    ALLOWED_ATTENDANCE_STATUSES,
    AttendanceStatus,
)
from modules.attendance.schemas import (
    AttendanceListItemResponse,
    AttendanceStatsResponse,
    AttendanceMeetingInfo,
    AttendanceEventInfo,
)

LOCAL_TZ = ZoneInfo("Asia/Ho_Chi_Minh")

DEFAULT_END_OF_DAY = time(18, 0)

def validate_status(status: str | None) -> None:
    """Kiểm tra giá trị status có hợp lệ không."""
    if status and status not in ALLOWED_ATTENDANCE_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Status không hợp lệ. Cho phép: {', '.join(sorted(ALLOWED_ATTENDANCE_STATUSES))}",
        )

def derive_status(
    target_date: date,
    schedule: WorkSchedule | None,
    check_in_time: datetime | None,
) -> str:
    """Suy luận trạng thái điểm danh dựa trên lịch và thời gian check-in."""
    if check_in_time is None:
        return AttendanceStatus.ABSENT

    if not schedule:
        return AttendanceStatus.ON_TIME

    tzinfo = check_in_time.tzinfo
    schedule_start = _build_schedule_datetime(
        target_date, schedule.start_time, tzinfo
    )

    late_cutoff = schedule_start + timedelta(
        minutes=schedule.late_threshold_minutes
    )
    if check_in_time > late_cutoff:
        return AttendanceStatus.LATE

    return AttendanceStatus.ON_TIME


def _build_schedule_datetime(
    target_date: date,
    schedule_time: time,
    tzinfo,
) -> datetime:
    """Ghép ngày và giờ ca làm việc thành datetime."""
    schedule_dt = datetime.combine(target_date, schedule_time)
    if tzinfo:
        schedule_dt = schedule_dt.replace(tzinfo=tzinfo)
    return schedule_dt

def compute_work_hours(
    check_in_time: datetime | None,
    record_date: date | None = None,
    now_ref: datetime | None = None,
) -> float | None:
    """Tính giờ làm việc từ check-in đến thời điểm hiện tại (hoặc cuối ngày nếu là ngày trước).

    - Ngày hôm nay: check_in → now
    - Ngày trước: check_in → cuối ca (hoặc 18:00 mặc định)
    """
    if not check_in_time:
        return None
    if now_ref is None:
        now_ref = datetime.now(LOCAL_TZ)
    today = now_ref.date()
    if record_date is None:
        record_date = today

    if record_date == today:
        end_time = now_ref
    else:
        tz = check_in_time.tzinfo or LOCAL_TZ
        end_time = datetime.combine(
            record_date, DEFAULT_END_OF_DAY, tzinfo=tz
        )

    delta = end_time - check_in_time
    hours = max(delta.total_seconds() / 3600, 0)
    return round(hours, 2)



def build_attendance_item(
    record,
    employee_name: str | None,
    meetings: list[AttendanceMeetingInfo] | None = None,
    events: list[AttendanceEventInfo] | None = None,
) -> AttendanceListItemResponse:
    """Chuyển bản ghi ORM sang response.

    work_hours được tính động từ check_in đến hiện tại (ngày hôm nay)
    hoặc đến cuối ca (ngày trước).
    """
    work_hours = compute_work_hours(record.check_in_time, record.date)
    return AttendanceListItemResponse(
        id=record.id,
        employee_id=record.employee_id,
        employee_name=employee_name,
        date=record.date,
        check_in_time=record.check_in_time,
        check_out_time=None,
        status=record.status,
        work_hours=work_hours,
        note=record.note,
        meetings=meetings or [],
        events=events or [],
    )

def build_stats(rows: list[tuple]) -> AttendanceStatsResponse:
    """Tính thống kê trạng thái từ danh sách bản ghi."""
    total = len(rows)
    status_counts = Counter(record.status for record, _ in rows)

    absent_count = status_counts.get(AttendanceStatus.ABSENT, 0)
    excused_count = status_counts.get(AttendanceStatus.EXCUSED, 0)
    present_count = total - absent_count - excused_count

    return AttendanceStatsResponse(
        total_employees=total,
        present_count=present_count,
        late_count=status_counts.get(AttendanceStatus.LATE, 0),
        absent_count=absent_count,
        excused_count=excused_count,
        on_time_count=status_counts.get(AttendanceStatus.ON_TIME, 0),
        early_leave_count=status_counts.get(AttendanceStatus.EARLY_LEAVE, 0),
        half_day_count=status_counts.get(AttendanceStatus.HALF_DAY, 0),
    )
