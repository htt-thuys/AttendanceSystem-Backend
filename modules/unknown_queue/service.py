from fastapi import HTTPException, UploadFile
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from modules.admin.schemas import UnknownQueueItemResponse
from modules.employees import support as employee_support
from modules.employees import repository as employees_repository
from modules.unknown_queue import repository
from storage.image_store import build_image_url, copy_to_avatar


async def list_unknown_queue(
    db: AsyncSession,
    event_id: int | None = None,
    meeting_id: int | None = None,
    event_scope: str | None = None,
    default_event_only: bool = False,
) -> list[UnknownQueueItemResponse]:
    """Lay du lieu unknown queue de admin hoac reviewer hien thi len giao dien."""
    normalized_scope = event_scope
    if default_event_only:
        normalized_scope = "default"
    if normalized_scope is not None and normalized_scope not in {"default", "inactive"}:
        raise HTTPException(status_code=400, detail="event_scope chi ho tro default hoac inactive")
    if (event_id is not None or meeting_id is not None) and normalized_scope is not None:
        raise HTTPException(status_code=400, detail="Chi duoc dung event_id/meeting_id hoac event_scope, khong dung dong thoi")
    if event_id is not None and meeting_id is not None:
        raise HTTPException(status_code=400, detail="Chi duoc dung event_id hoac meeting_id, khong dung ca hai")

    rows = await repository.list_unknown_queue_records(
        db,
        event_id=event_id,
        meeting_id=meeting_id,
        event_scope=normalized_scope,
    )
    return [
        UnknownQueueItemResponse(
            id=record.id,
            camera_id=record.camera_id,
            event_id=record.event_id,
            event_title=event_title,
            meeting_id=record.meeting_id,
            meeting_title=meeting_title,
            image_path=record.image_path,
            image_url=build_image_url(record.image_path),
            attempt_count=record.attempt_count,
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
            face_quality=record.face_quality,
        )
        for record, event_title, meeting_title in rows
    ]


async def create_employee_from_unknown_queue(
    db: AsyncSession,
    queue_id: int,
    full_name: str,
    employee_code: str,
    avatar: UploadFile | None,
    vector_images: list[UploadFile] | None,
) -> tuple[bool, int]:
    """Tao nhan vien tu unknown queue, giu vector dau tien dung voi anh tot nhat trong queue."""
    unknown_record = await get_unknown_record_or_404(db=db, queue_id=queue_id)
    clean_vector_files = employee_support.normalize_upload_files(files=vector_images)
    employee_support.validate_vector_upload_limit(clean_vector_files)
    avatar_bytes = await employee_support.read_optional_file(upload_file=avatar)

    try:
        employee = await employees_repository.create_employee_record(
            db=db,
            full_name=full_name,
            employee_code=employee_code,
            avatar_path=None,
        )

        if avatar_bytes:
            from storage.image_store import save_avatar_image

            employee.avatar_path = await save_avatar_image(
                image_bytes=avatar_bytes,
                employee_id=employee.id,
                original_name=avatar.filename if avatar else None,
            )
        else:
            employee.avatar_path = await copy_to_avatar(
                source_relative_path=unknown_record.image_path,
                employee_id=employee.id,
            )

        await employee_support.create_face_vector_from_existing_source(
            db=db,
            employee_id=employee.id,
            vector=unknown_record.vector,
            source_image_path=unknown_record.image_path,
            source="manual",
            quality_score=unknown_record.face_quality,
        )

        for upload_file in clean_vector_files:
            await employee_support.create_face_vector_from_upload(
                db=db,
                employee_id=employee.id,
                upload_file=upload_file,
                source="manual",
            )

        unknown_record.resolved_at = func.now()
        await db.commit()
        return True, employee.id
    except IntegrityError as error:
        await db.rollback()
        if "unique" in str(error).lower():
            raise HTTPException(
                status_code=400,
                detail="Ma nhan vien (employee_code) da ton tai. Vui long chon ma khac!",
            )
        raise


async def assign_unknown_queue(
    db: AsyncSession,
    queue_id: int,
    employee_id: int,
) -> bool:
    """Gan unknown queue cho nhan vien cu va luu luon diem giong khi tao vector."""
    unknown_record = await get_unknown_record_or_404(db=db, queue_id=queue_id)
    employee = await employees_repository.get_employee_record(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")
    if employee.status != "active":
        raise HTTPException(status_code=400, detail="Chi duoc gan unknown queue cho nhan vien dang active")

    await employee_support.create_face_vector_from_existing_source(
        db=db,
        employee_id=employee_id,
        vector=unknown_record.vector,
        source_image_path=unknown_record.image_path,
        source="manual",
        quality_score=unknown_record.face_quality,
    )
    unknown_record.resolved_at = func.now()
    await db.commit()
    return True


async def reject_unknown_queue(db: AsyncSession, queue_id: int) -> bool:
    """Danh dau unknown queue la da xu ly tu choi, khong xoa anh ngay de cleanup xu ly sau."""
    unknown_record = await get_unknown_record_or_404(db=db, queue_id=queue_id)
    unknown_record.resolved_at = func.now()
    await db.commit()
    return True


async def get_unknown_record_or_404(db: AsyncSession, queue_id: int):
    """Lay unknown queue chua xu ly theo id, neu khong co thi tra loi 404."""
    record = await repository.get_unknown_queue_record(db, queue_id)
    if not record:
        raise HTTPException(status_code=404, detail="Ban ghi khong ton tai hoac da xu ly")
    return record
