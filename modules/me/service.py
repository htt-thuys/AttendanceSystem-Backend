from datetime import date

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password, verify_password
from infrastructure.database.models import Employee, User
from modules.employees import repository as employees_repository
from modules.recognition_logs import repository as recognition_logs_repository
from modules.me.schemas import (
    MyPasswordUpdateRequest,
    MyProfileResponse,
    MyRecognitionLogItemResponse,
    SelfActionResponse,
)
from storage.image_store import build_image_url, save_avatar_image
from modules.users import repository as users_repository


async def get_my_profile(db: AsyncSession, current_user: User) -> MyProfileResponse:
    employee = await _get_linked_employee(db=db, current_user=current_user)
    return _build_my_profile_response(current_user=current_user, employee=employee)


async def update_my_profile(
    db: AsyncSession,
    current_user: User,
    full_name: str | None,
    email: str | None,
    avatar: UploadFile | None,
) -> MyProfileResponse:
    normalized_email = _normalize_optional_text(email)
    normalized_full_name = _normalize_optional_text(full_name)
    employee = await _get_linked_employee(db=db, current_user=current_user)

    if normalized_email != current_user.email:
        await _ensure_email_available(db=db, email=normalized_email, current_user=current_user)
        current_user.email = normalized_email

    if normalized_full_name is not None or avatar is not None:
        if not employee:
            raise HTTPException(
                status_code=400,
                detail="Tai khoan hien tai chua lien ket voi ho so nhan vien de cap nhat thong tin ca nhan",
            )

        if normalized_full_name is not None:
            employee.full_name = normalized_full_name

        if avatar is not None:
            avatar_bytes = await avatar.read()
            if not avatar_bytes:
                raise HTTPException(status_code=400, detail="Anh avatar tai len dang rong")
            employee.avatar_path = await save_avatar_image(
                image_bytes=avatar_bytes,
                employee_id=employee.id,
                original_name=avatar.filename,
            )

    await db.commit()
    await db.refresh(current_user)
    if employee:
        await db.refresh(employee)
    return _build_my_profile_response(current_user=current_user, employee=employee)


async def update_my_password(
    db: AsyncSession,
    current_user: User,
    payload: MyPasswordUpdateRequest,
) -> SelfActionResponse:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Mat khau hien tai khong chinh xac")

    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="Mat khau moi phai khac mat khau hien tai")

    current_user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return SelfActionResponse(success=True, message="Da cap nhat mat khau")


async def list_my_recognition_logs_today(
    db: AsyncSession,
    current_user: User,
    limit: int = 100,
) -> list[MyRecognitionLogItemResponse]:
    if current_user.employee_id is None:
        return []

    rows = await recognition_logs_repository.list_recognition_logs(
        db=db,
        date_value=date.today(),
        employee_id=current_user.employee_id,
        limit=limit,
    )
    return [
        MyRecognitionLogItemResponse(
            id=log_entry.id,
            camera_id=log_entry.camera_id,
            captured_at=log_entry.captured_at,
            face_image_path=log_entry.face_image_path,
            face_image_url=build_image_url(log_entry.face_image_path),
            result_label=log_entry.result_label,
            top_score=log_entry.top_score,
            final_label=log_entry.final_label,
            resolved_at=log_entry.resolved_at,
        )
        for log_entry, _employee_name, _event_title in rows
    ]


async def _get_linked_employee(db: AsyncSession, current_user: User) -> Employee | None:
    if current_user.employee_id is None:
        return None
    return await employees_repository.get_employee_record(db, current_user.employee_id)


async def _ensure_email_available(
    db: AsyncSession,
    email: str | None,
    current_user: User,
) -> None:
    if not email:
        return

    existing_user = await users_repository.get_user_by_email(db, email)
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(status_code=400, detail="Email da duoc su dung")


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _build_my_profile_response(
    current_user: User,
    employee: Employee | None,
) -> MyProfileResponse:
    return MyProfileResponse(
        user_id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        employee_id=current_user.employee_id,
        full_name=employee.full_name if employee else None,
        employee_code=employee.employee_code if employee else None,
        avatar_path=employee.avatar_path if employee else None,
        avatar_url=build_image_url(employee.avatar_path) if employee else None,
        employee_status=employee.status if employee else None,
        created_at=current_user.created_at,
    )
