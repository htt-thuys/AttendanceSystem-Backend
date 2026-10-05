"""Centralized enums for attendance statuses."""

from enum import StrEnum

class AttendanceStatus(StrEnum):
    ON_TIME = "on_time"
    LATE = "late"
    ABSENT = "absent"
    EXCUSED = "excused"
    HALF_DAY = "half_day"
    EARLY_LEAVE = "early_leave"

class EmployeeStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"

class RecognitionLabel(StrEnum):
    CONFIRMED = "confirmed"

ALLOWED_ATTENDANCE_STATUSES = set(AttendanceStatus)
