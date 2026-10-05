from datetime import date

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from modules.employees import repository as employees_repository
from modules.recognition_logs import repository
from modules.admin.schemas import RecognitionLogItemResponse
from storage.image_store import build_image_url

ALLOWED_RESULT_LABELS = {"sure", "review", "unknown"}
ALLOWED_FINAL_LABELS = {"confirmed", "rejected"}


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
) -> list[RecognitionLogItemResponse]:
    """Lay danh sach recognition log theo cac bo loc de admin xem log tong quat hoac log trong ngay."""
    _validate_filters(
        date_from=date_from,
        date_to=date_to,
        result_label=result_label,
        final_label=final_label,
    )
    rows = await repository.list_recognition_logs(
        db=db,
        date_value=date_value,
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        default_event_only=default_event_only,
        employee_id=employee_id,
        result_label=result_label,
        final_label=final_label,
        include_pending=include_pending,
        public_visible_only=public_visible_only,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return [
        _build_recognition_log_response(log_entry, employee_name, event_title, meeting_title)
        for log_entry, employee_name, event_title, meeting_title in rows
    ]


async def list_recent_public_recognition_logs(
    db: AsyncSession,
    camera_id: int | None = None,
    event_id: int | None = None,
    meeting_id: int | None = None,
    default_event_only: bool = False,
    limit: int = 20,
) -> list[RecognitionLogItemResponse]:
    """Lay recognition logs gan day cho man hinh tablet public."""
    return await list_recognition_logs(
        db=db,
        camera_id=camera_id,
        event_id=event_id,
        meeting_id=meeting_id,
        default_event_only=default_event_only,
        public_visible_only=True,
        limit=limit,
    )


async def list_employee_recognition_logs(
    db: AsyncSession,
    emp_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = 100,
) -> list[RecognitionLogItemResponse]:
    """Lay lich su recognition log cua rieng mot nhan vien cho tab History ben admin."""
    employee = await employees_repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")

    return await list_recognition_logs(
        db=db,
        employee_id=emp_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )


def _build_recognition_log_response(
    log_entry,
    employee_name: str | None,
    event_title: str | None,
    meeting_title: str | None,
) -> RecognitionLogItemResponse:
    """Doi ORM recognition log thanh response gon de FE dung cho bang log va lich su."""
    return RecognitionLogItemResponse(
        id=log_entry.id,
        camera_id=log_entry.camera_id,
        event_id=log_entry.event_id,
        event_title=event_title,
        meeting_id=log_entry.meeting_id,
        meeting_title=meeting_title,
        captured_at=log_entry.captured_at,
        face_image_path=log_entry.face_image_path,
        face_image_url=build_image_url(log_entry.face_image_path),
        result_label=log_entry.result_label,
        top_score=log_entry.top_score,
        employee_id=log_entry.employee_id,
        employee_name=employee_name,
        final_label=log_entry.final_label,
        resolved_at=log_entry.resolved_at,
    )


def _validate_filters(
    date_from: date | None,
    date_to: date | None,
    result_label: str | None,
    final_label: str | None,
) -> None:
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from phai truoc hoac bang date_to")
    if result_label and result_label not in ALLOWED_RESULT_LABELS:
        allowed = ", ".join(sorted(ALLOWED_RESULT_LABELS))
        raise HTTPException(status_code=400, detail=f"result_label khong hop le. Cho phep: {allowed}")
    if final_label and final_label not in ALLOWED_FINAL_LABELS:
        allowed = ", ".join(sorted(ALLOWED_FINAL_LABELS))
        raise HTTPException(status_code=400, detail=f"final_label khong hop le. Cho phep: {allowed}")
