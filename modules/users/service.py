from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password
from infrastructure.database.models import AdminLog, Employee, RecognitionLog, SystemSetting, UnknownQueue, User
from modules.admin.schemas import (
    AdminActionResponse,
    EmployeeAccountCreateRequest,
    EmployeeAccountResponse,
    UserPasswordUpdateRequest,
    UserStatusUpdateRequest,
)
from modules.employees import repository as employees_repository
from modules.users import repository

ALLOWED_ACCOUNT_ROLES = {"admin", "reviewer", "employee"}


async def get_employee_account(db: AsyncSession, emp_id: int) -> EmployeeAccountResponse:
    """Lay tai khoan dang lien ket voi nhan vien de admin xem tab Account."""
    employee = await employees_repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")

    user = await repository.get_user_by_employee_id(db, emp_id)
    if not user:
        raise HTTPException(status_code=404, detail="Nhan vien chua co tai khoan")

    return build_employee_account_response(user)


async def create_employee_account(
    db: AsyncSession,
    emp_id: int,
    payload: EmployeeAccountCreateRequest,
) -> EmployeeAccountResponse:
    """Tao tai khoan dang nhap moi va lien ket truc tiep voi nhan vien tuong ung."""
    employee = await employees_repository.get_employee_record(db, emp_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Khong tim thay nhan vien")

    existing_linked_user = await repository.get_user_by_employee_id(db, emp_id)
    if existing_linked_user:
        raise HTTPException(status_code=400, detail="Nhan vien nay da co tai khoan")

    existing_username_user = await repository.get_user_by_username(db, payload.username)
    if existing_username_user:
        raise HTTPException(status_code=400, detail="Username da duoc su dung")

    if payload.email:
        existing_email_user = await repository.get_user_by_email(db, payload.email)
        if existing_email_user:
            raise HTTPException(status_code=400, detail="Email da duoc su dung")

    validate_user_role(payload.role)
    user = await repository.create_user_record(
        db=db,
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        employee_id=emp_id,
    )
    await db.commit()
    await db.refresh(user)
    return build_employee_account_response(user)


async def update_user_password(
    db: AsyncSession,
    user_id: int,
    payload: UserPasswordUpdateRequest,
) -> AdminActionResponse:
    """Dat lai mat khau cho mot tai khoan do admin quan ly."""
    user = await repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay tai khoan")

    user.password_hash = hash_password(payload.password)
    await db.commit()
    return AdminActionResponse(success=True, message="Da cap nhat mat khau")


async def update_user_status(
    db: AsyncSession,
    user_id: int,
    payload: UserStatusUpdateRequest,
) -> EmployeeAccountResponse:
    """Khoa hoac mo lai trang thai hoat dong cua mot tai khoan."""
    user = await repository.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Khong tim thay tai khoan")

    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)
    return build_employee_account_response(user)


def build_employee_account_response(user: User) -> EmployeeAccountResponse:
    """Doi ORM user thanh response account de admin hien thi tren tab quan ly tai khoan."""
    return EmployeeAccountResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        employee_id=user.employee_id,
        created_at=user.created_at,
    )


def validate_user_role(role: str) -> None:
    """Kiem tra role account co thuoc danh sach he thong dang ho tro hay khong."""
    if role not in ALLOWED_ACCOUNT_ROLES:
        allowed_roles = ", ".join(sorted(ALLOWED_ACCOUNT_ROLES))
        raise HTTPException(
            status_code=400,
            detail=f"Role khong hop le. Chi ho tro: {allowed_roles}",
        )


async def cleanup_user_links_before_delete(db: AsyncSession, user: User) -> None:
    """Don cac lien ket nullable cua user truoc khi xoa han account."""
    employee_query = await db.execute(
        select(Employee).where(Employee.created_by == user.id)
    )
    for employee in employee_query.scalars().all():
        employee.created_by = None

    recognition_query = await db.execute(
        select(RecognitionLog).where(RecognitionLog.resolved_by == user.id)
    )
    for log_entry in recognition_query.scalars().all():
        log_entry.resolved_by = None

    unknown_query = await db.execute(
        select(UnknownQueue).where(UnknownQueue.resolved_by == user.id)
    )
    for queue_entry in unknown_query.scalars().all():
        queue_entry.resolved_by = None

    setting_query = await db.execute(
        select(SystemSetting).where(SystemSetting.updated_by == user.id)
    )
    for setting_record in setting_query.scalars().all():
        setting_record.updated_by = None

    admin_log_query = await db.execute(
        select(AdminLog).where(AdminLog.admin_id == user.id)
    )
    for admin_log in admin_log_query.scalars().all():
        await db.delete(admin_log)
