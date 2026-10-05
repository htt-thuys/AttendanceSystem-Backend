"""Meetings service package."""

from modules.meetings.services.attendance_service import (
    checkin_participant,
    checkout_participant,
    request_absence,
)
from modules.meetings.services.meeting_service import (
    cancel_meeting,
    complete_meeting,
    create_meeting,
    get_meeting_detail,
    list_meetings,
    list_active_public_meetings,
    update_meeting,
)
from modules.meetings.services.participant_service import (
    add_participants,
    get_meeting_attendance,
    remove_participant,
)
from modules.meetings.services.recognition_service import (
    apply_unknown_assignment_to_meetings,
    auto_checkin_by_camera,
    auto_checkin_selected_meeting,
    ensure_recognition_meeting_context,
)

__all__ = [
    "add_participants",
    "apply_unknown_assignment_to_meetings",
    "auto_checkin_by_camera",
    "auto_checkin_selected_meeting",
    "cancel_meeting",
    "checkin_participant",
    "checkout_participant",
    "complete_meeting",
    "create_meeting",
    "ensure_recognition_meeting_context",
    "get_meeting_attendance",
    "get_meeting_detail",
    "list_meetings",
    "list_active_public_meetings",
    "remove_participant",
    "request_absence",
    "update_meeting",
]
