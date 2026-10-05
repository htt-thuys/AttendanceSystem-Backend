"""Centralized enums for meeting and participant statuses."""

from enum import StrEnum
from datetime import timedelta

class MeetingStatus(StrEnum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class ParticipantStatus(StrEnum):
    INVITED = "invited"
    PRESENT = "present"
    LATE = "late"
    ABSENT = "absent"
    EXCUSED = "excused"

ALLOWED_MEETING_STATUSES = set(MeetingStatus)
CHECKIN_ALLOWED_STATUSES = {MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS}
RECOGNITION_ALLOWED_STATUSES = {MeetingStatus.SCHEDULED, MeetingStatus.IN_PROGRESS, MeetingStatus.COMPLETED}
CHECKOUT_ALLOWED_STATUSES = {MeetingStatus.IN_PROGRESS, MeetingStatus.COMPLETED}

ABSENCE_REQUEST_MIN_NOTICE = timedelta(minutes=30)
