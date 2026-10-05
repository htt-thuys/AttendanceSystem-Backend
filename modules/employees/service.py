import uuid

from fastapi import HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from infrastructure.vector_db.qdrant_client import delete_vectors, set_vectors_active
from modules.admin.schemas import AdminActionResponse, EmployeeListItemResponse, EmployeeVectorItemResponse
from modules.employees import repository
from modules.employees import support
from modules.users import repository as users_repository
from storage.image_store import build_image_url, delete_image, save_avatar_image


async def list_employees(
    db: AsyncSession,
    status_filter: str | None = None,
) -> list[EmployeeListItemResponse]:
    """Lay danh sach nhan vien kem avatar va so vector active."""
    if status_filter is not None and status_filter not in {"active", "inactive"}:
        raise HTTPException(status_code=400, detail="status chi ho tro active hoac inactive")

    rows = await repository.list_employee_records(db, status=status_filter)
    return _build_employee_list_response(rows)


async def list_active_public_employees(db: AsyncSession) -> list[EmployeeListItemResponse]:
    """Lay danh sach nhan vien active cho man tablet chon lai nguoi dung."""
    rows = await repository.list_employee_records(db, status="active")
    return _build_employee_list_response(rows)


def _build_employee_list_response(rows) -> list[EmployeeListItemResponse]:
    return [
        EmployeeListItemResponse(
            id=employee.id,
            full_name=employee.full_name,
            employee_code=employee.employee_code,
            avatar_path=employee.avatar_path,
            avatar_url=build_image_url(employee.avatar_path),
            status=employee.status,
            vector_count=int(vector_count),
        )
        for employee, vector_count in rows
    ]


async def list_employee_vectors(
    db: AsyncSession,
    emp_id: int,
) -> list[EmployeeVectorItemResponse]:
    """Lay danh sach vector active cua nhan vien kem dung anh nguon va diem tao vector."""
    employee = await repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")

    vectors = await repository.get_employee_vector_records(db, emp_id)
    return [
        EmployeeVectorItemResponse(
            id=vector.id,
            source=vector.source,
            source_image_path=vector.source_image_path,
            source_image_url=build_image_url(vector.source_image_path),
            quality_score=vector.quality_score,
            score_at_create=vector.score_at_create,
            created_at=vector.created_at,
        )
        for vector in vectors
    ]


async def create_employee(
    db: AsyncSession,
    full_name: str,
    employee_code: str,
    avatar: UploadFile,
    vector_images: list[UploadFile] | None,
) -> tuple[bool, int]:
    """Tao nhan vien moi tu avatar va toi da 5 anh bo sung de sinh vector."""
    avatar_bytes = await support.read_required_file(upload_file=avatar, field_name="avatar")
    clean_vector_files = support.normalize_upload_files(files=vector_images)
    support.validate_vector_upload_limit(clean_vector_files)

    try:
        employee = await repository.create_employee_record(
            db=db,
            full_name=full_name,
            employee_code=employee_code,
            avatar_path=None,
        )

        employee.avatar_path = await save_avatar_image(
            image_bytes=avatar_bytes,
            employee_id=employee.id,
            original_name=avatar.filename,
        )

        if clean_vector_files:
            for upload_file in clean_vector_files:
                await support.create_face_vector_from_upload(
                    db=db,
                    employee_id=employee.id,
                    upload_file=upload_file,
                    source="manual",
                )
        else:
            await support.create_face_vector_from_avatar(
                db=db,
                employee_id=employee.id,
                avatar_bytes=avatar_bytes,
                avatar_name=avatar.filename,
            )

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


async def update_employee_avatar(
    db: AsyncSession,
    emp_id: int,
    avatar: UploadFile,
) -> bool:
    """Doi avatar cho nhan vien ma khong lam thay doi cac vector dang co."""
    employee = await repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")
    if employee.status == "deleted":
        raise HTTPException(status_code=400, detail="Nhan vien da bi xoa/anonymize")

    avatar_bytes = await support.read_required_file(upload_file=avatar, field_name="avatar")
    await delete_image(employee.avatar_path)
    employee.avatar_path = await save_avatar_image(
        image_bytes=avatar_bytes,
        employee_id=employee.id,
        original_name=avatar.filename,
    )
    await db.commit()
    return True


async def add_employee_vectors(
    db: AsyncSession,
    emp_id: int,
    vector_images: list[UploadFile] | None,
) -> bool:
    """Bo sung toi da 5 vector moi cho nhan vien cu bang anh upload truc tiep."""
    employee = await repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")
    if employee.status == "deleted":
        raise HTTPException(status_code=400, detail="Nhan vien da bi xoa/anonymize")

    clean_vector_files = support.normalize_upload_files(files=vector_images)
    if not clean_vector_files:
        raise HTTPException(status_code=400, detail="Can it nhat 1 anh de bo sung vector")
    support.validate_vector_upload_limit(clean_vector_files)

    for upload_file in clean_vector_files:
        await support.create_face_vector_from_upload(
            db=db,
            employee_id=employee.id,
            upload_file=upload_file,
            source="manual",
        )

    await db.commit()
    return True


async def delete_employee_vector(db: AsyncSession, emp_id: int, vec_id: int) -> bool:
    """Xoa han mot vector cua nhan vien va point tuong ung trong Qdrant."""
    vector = await repository.get_employee_vector_record(db, emp_id, vec_id)
    if not vector:
        raise HTTPException(status_code=404, detail="Khong tim thay vector")

    delete_vectors([vector.qdrant_point_id])
    await delete_image(vector.source_image_path)
    await db.delete(vector)
    await db.commit()
    return True


async def deactivate_employee(db: AsyncSession, emp_id: int) -> AdminActionResponse:
    """Vo hieu hoa nhan vien, toan bo vector va account lien ket neu co."""
    employee = await repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")
    if employee.status == "deleted":
        raise HTTPException(status_code=400, detail="Nhan vien da bi xoa/anonymize")

    linked_user = await users_repository.get_user_by_employee_id(db, emp_id)
    vectors = await repository.get_employee_vector_records(db, emp_id, include_inactive=True)

    employee.status = "inactive"
    point_ids = []
    for vector in vectors:
        vector.is_active = False
        point_ids.append(vector.qdrant_point_id)

    set_vectors_active(point_ids, False)

    if linked_user:
        linked_user.is_active = False

    await db.commit()
    return AdminActionResponse(success=True, message="Da vo hieu hoa nhan vien")


async def reactivate_employee(db: AsyncSession, emp_id: int) -> AdminActionResponse:
    """Kich hoat lai nhan vien, account lien ket va toan bo vector cua nhan vien do."""
    employee = await repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")
    if employee.status == "deleted":
        raise HTTPException(status_code=400, detail="Nhan vien da bi xoa/anonymize, khong the kich hoat lai")

    linked_user = await users_repository.get_user_by_employee_id(db, emp_id)
    vectors = await repository.get_employee_vector_records(db, emp_id, include_inactive=True)

    employee.status = "active"
    point_ids = []
    for vector in vectors:
        vector.is_active = True
        point_ids.append(vector.qdrant_point_id)

    set_vectors_active(point_ids, True)

    if linked_user:
        linked_user.is_active = True

    await db.commit()
    return AdminActionResponse(success=True, message="Da kich hoat lai nhan vien")


async def anonymize_employee(db: AsyncSession, emp_id: int) -> AdminActionResponse:
    """Anonymize nhan vien, giu ID/FK lich su va xoa du lieu sinh trac."""
    employee = await repository.get_employee_record(db, emp_id, include_deleted=True)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")
    if employee.status == "deleted":
        return AdminActionResponse(success=True, message="Nhan vien da duoc anonymize truoc do")

    linked_user = await users_repository.get_user_by_employee_id(db, emp_id)
    vectors = await repository.get_employee_vector_records(db, emp_id, include_inactive=True)
    point_ids = [vector.qdrant_point_id for vector in vectors]

    delete_vectors(point_ids)
    for vector in vectors:
        await delete_image(vector.source_image_path)
    await repository.delete_face_vectors_by_employee_id(db, emp_id)

    logs = await repository.list_recognition_logs_by_employee_id(db, emp_id)
    for log_entry in logs:
        await delete_image(log_entry.face_image_path)
        log_entry.face_image_path = None

    await delete_image(employee.avatar_path)
    employee.full_name = f"Deleted Employee #{employee.id}"
    employee.employee_code = f"deleted_emp_{employee.id}_{uuid.uuid4().hex[:12]}"
    employee.avatar_path = None
    employee.status = "deleted"
    employee.metadata_ = {}

    if linked_user:
        linked_user.username = f"deleted_user_{linked_user.id}_{uuid.uuid4().hex[:12]}"
        linked_user.email = None
        linked_user.password_hash = hash_password(uuid.uuid4().hex)
        linked_user.role = "employee"
        linked_user.is_active = False

    await db.commit()
    return AdminActionResponse(success=True, message="Da anonymize nhan vien", employee_id=employee.id)
