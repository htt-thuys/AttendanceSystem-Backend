"""Pure helper functions for the meetings module (no DB access)."""

from collections import Counter
from datetime import datetime, timezone

from fastapi import HTTPException

from infrastructure.database.models import Meeting
from modules.meetings import repository
from modules.meetings.enums import (
    ALLOWED_MEETING_STATUSES,
    CHECKIN_ALLOWED_STATUSES,
    RECOGNITION_ALLOWED_STATUSES,
    MeetingStatus,
    ParticipantStatus,
)
from modules.meetings.schemas import (
    MeetingDetailResponse,
    MeetingParticipantResponse,
)

def as_aware_utc(value: datetime) -> datetime:
    """Chuẩn hóa datetime sang timezone UTC để so sánh an toàn."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

def validate_meeting_status(status: str) -> None:
    """Kiểm tra meeting status có hợp lệ không."""
    if status not in ALLOWED_MEETING_STATUSES:
        allowed = ", ".join(sorted(ALLOWED_MEETING_STATUSES))
        raise HTTPException(
            status_code=400,
            detail=f"Trang thai khong hop le. Chi ho tro: {allowed}",
        )

def validate_schedule(start_at, end_at) -> None:
    if end_at and start_at and end_at < start_at:
        raise HTTPException(
            status_code=400,
            detail="Thoi gian ket thuc phai sau thoi gian bat dau",
        )

def ensure_meeting_allows_checkin(meeting: Meeting) -> None:
    """Kiểm tra cuộc họp có cho phép check-in hay không."""
    if meeting.status not in CHECKIN_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Cuoc hop da ket thuc hoac da bi huy, khong the check-in",
        )

def ensure_meeting_matches_camera(meeting: Meeting, camera_id: int | None) -> None:
    if (
        camera_id is not None
        and meeting.camera_id is not None
        and meeting.camera_id != camera_id
    ):
        raise HTTPException(
            status_code=400,
            detail="camera_id khong khop voi cuoc hop da chon",
        )

def ensure_meeting_allows_recognition_checkin(
    meeting: Meeting,
    captured_at: datetime,
) -> None:
    if meeting.status not in RECOGNITION_ALLOWED_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Cuoc hop khong cho phep diem danh bang nhan dien",
        )

    captured_at = as_aware_utc(captured_at)
    start_at = as_aware_utc(meeting.scheduled_start)
    if captured_at < start_at - repository.EARLY_CHECKIN_WINDOW:
        raise HTTPException(
            status_code=400,
            detail="Chua den thoi gian diem danh cuoc hop",
        )

    if meeting.scheduled_end is not None:
        end_at = as_aware_utc(meeting.scheduled_end)
        if captured_at > end_at + repository.POST_END_MATCH_WINDOW:
            raise HTTPException(
                status_code=400,
                detail="Da qua thoi gian diem danh cuoc hop",
            )

def derive_meeting_attendance_status(
    meeting: Meeting,
    captured_at: datetime,
) -> str:
    """Suy luận status meeting attendance từ thời điểm check-in/capture."""
    captured_at = as_aware_utc(captured_at)
    start_at = as_aware_utc(meeting.scheduled_start)
    end_at = (
        as_aware_utc(meeting.scheduled_end) if meeting.scheduled_end else None
    )
    if captured_at < start_at:
        return ParticipantStatus.PRESENT
    if end_at is not None and captured_at > end_at:
        return ParticipantStatus.ABSENT
    return ParticipantStatus.LATE

def build_meeting_detail_response(
    meeting: Meeting,
    participants: list[MeetingParticipantResponse],
) -> MeetingDetailResponse:
    return MeetingDetailResponse(
        id=meeting.id,
        title=meeting.title,
        description=meeting.description,
        scheduled_start=meeting.scheduled_start,
        scheduled_end=meeting.scheduled_end,
        actual_start=meeting.actual_start,
        actual_end=meeting.actual_end,
        location=meeting.location,
        camera_id=meeting.camera_id,
        status=meeting.status,
        created_by=meeting.created_by,
        created_at=meeting.created_at,
        updated_at=meeting.updated_at,
        participants=participants,
    )

def build_checkin_message(meeting_title: str, status: str) -> str:
    """Tạo message ngắn để FE hiển thị popup sau khi check-in."""
    if status == ParticipantStatus.ABSENT:
        return f"The meeting {meeting_title} ended"
    return f"Attendance check {meeting_title}"

def build_meeting_invitation_email(message: str, data: dict) -> str:
    meeting_id = data.get("meeting_id")
    lines = [message]
    if meeting_id is not None:
        lines.append(f"Meeting ID: {meeting_id}")
    lines.append("")
    lines.append(
        "Please check your Attendance System notifications for details."
    )
    return "\n".join(lines)

def count_participant_statuses(
    participants: list[MeetingParticipantResponse],
) -> Counter:
    """Đếm số lượng participant theo status bằng Counter."""
    return Counter(p.status for p in participants)
