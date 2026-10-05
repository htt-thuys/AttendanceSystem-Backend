from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from infrastructure.ai_client import AIClientError, extract_face_data
from infrastructure.vector_db.qdrant_client import search_vectors, upsert_vector
from modules.employees import repository
from storage.image_store import (
    copy_to_vector_source,
    save_vector_source_image,
)


def normalize_upload_files(files: list[UploadFile] | None) -> list[UploadFile]:
    """Loc danh sach upload file, chi giu cac file thuc su co ten va ton tai."""
    clean_files: list[UploadFile] = []
    for upload_file in files or []:
        if upload_file and upload_file.filename:
            clean_files.append(upload_file)
    return clean_files


def validate_vector_upload_limit(files: list[UploadFile]) -> None:
    """Kiem tra so luong anh vector upload moi lan co vuot nguong cau hinh hay khong."""
    if len(files) > settings.ADMIN_VECTOR_UPLOAD_LIMIT:
        raise HTTPException(
            status_code=400,
            detail=f"Moi lan chi duoc upload toi da {settings.ADMIN_VECTOR_UPLOAD_LIMIT} anh vector",
        )


async def read_required_file(upload_file: UploadFile, field_name: str) -> bytes:
    """Doc bytes cua file bat buoc, bao loi neu thieu hoac file rong."""
    file_bytes = await upload_file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail=f"Thieu file {field_name}")
    return file_bytes


async def read_optional_file(upload_file: UploadFile | None) -> bytes | None:
    """Doc bytes cua file tuy chon, tra ve None neu khong co du lieu."""
    if not upload_file or not upload_file.filename:
        return None
    file_bytes = await upload_file.read()
    return file_bytes or None


async def create_face_vector_from_avatar(
    db: AsyncSession,
    employee_id: int,
    avatar_bytes: bytes,
    avatar_name: str | None,
) -> None:
    """Sinh vector dau tien tu avatar va luu rieng anh nguon vector de khong dung avatar."""
    try:
        face_data = await extract_face_data(avatar_bytes, filename=avatar_name or "avatar.jpg")
    except AIClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if face_data is None:
        raise HTTPException(status_code=400, detail="Anh avatar khong nhan dien duoc khuon mat")

    source_image_path = await save_vector_source_image(
        image_bytes=avatar_bytes,
        original_name=avatar_name,
    )
    await create_face_vector_record(
        db=db,
        employee_id=employee_id,
        vector=face_data["vector"],
        source="manual",
        source_image_path=source_image_path,
        quality_score=face_data["face_quality"],
    )


async def create_face_vector_from_upload(
    db: AsyncSession,
    employee_id: int,
    upload_file: UploadFile,
    source: str,
) -> None:
    """Sinh vector tu mot anh upload moi va tinh diem giong tai luc luu neu co du lieu cu."""
    image_bytes = await upload_file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Co anh upload rong, vui long chon lai")

    try:
        face_data = await extract_face_data(
            image_bytes,
            filename=upload_file.filename or "upload.jpg",
            content_type=upload_file.content_type or "image/jpeg",
        )
    except AIClientError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc

    if face_data is None:
        raise HTTPException(
            status_code=400,
            detail=f"Anh '{upload_file.filename}' khong nhan dien duoc khuon mat",
        )

    source_image_path = await save_vector_source_image(
        image_bytes=image_bytes,
        original_name=upload_file.filename,
    )
    await create_face_vector_record(
        db=db,
        employee_id=employee_id,
        vector=face_data["vector"],
        source=source,
        source_image_path=source_image_path,
        quality_score=face_data["face_quality"],
    )


async def create_face_vector_from_existing_source(
    db: AsyncSession,
    employee_id: int,
    vector: list[float],
    source_image_path: str,
    source: str,
    quality_score: float | None,
) -> None:
    """Copy anh nguon san co sang kho vector source roi luu vector moi cho nhan vien."""
    vector_source_path = await copy_to_vector_source(source_image_path)
    await create_face_vector_record(
        db=db,
        employee_id=employee_id,
        vector=vector,
        source=source,
        source_image_path=vector_source_path,
        quality_score=quality_score,
    )


async def create_face_vector_record(
    db: AsyncSession,
    employee_id: int,
    vector: list[float],
    source: str | None,
    source_image_path: str,
    quality_score: float | None,
) -> None:
    """Tao metadata vector, tinh score_at_create va upsert point tuong ung len Qdrant."""
    score_at_create = calculate_score_at_create(employee_id=employee_id, vector=vector)
    face_vector = await repository.create_face_vector_record(
        db=db,
        employee_id=employee_id,
        source=source,
        source_image_path=source_image_path,
        quality_score=quality_score,
        score_at_create=score_at_create,
    )
    face_vector.qdrant_point_id = face_vector.id
    payload = {
        "employee_id": employee_id,
        "face_vec_id": face_vector.id,
        "is_active": True,
    }
    upsert_vector(face_vector.id, vector, payload)


def calculate_score_at_create(employee_id: int, vector: list[float]) -> float | None:
    """Tinh diem giong cao nhat giua vector moi va cac vector active hien co cua nhan vien."""
    points = search_vectors(
        vector=vector,
        top=1,
        only_active=True,
        employee_id=employee_id,
    )
    if not points:
        return None
    return float(points[0].score)
