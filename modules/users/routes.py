from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.admin.schemas import (
    AdminActionResponse,
    EmployeeAccountCreateRequest,
    EmployeeAccountResponse,
    UserPasswordUpdateRequest,
    UserStatusUpdateRequest,
)
from modules.users import service

router = APIRouter()


@router.get("/employees/{emp_id}/account", response_model=EmployeeAccountResponse)
async def get_employee_account(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.get_employee_account(db=db, emp_id=emp_id)


@router.post("/employees/{emp_id}/account", response_model=EmployeeAccountResponse)
async def create_employee_account(
    emp_id: int,
    payload: EmployeeAccountCreateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.create_employee_account(db=db, emp_id=emp_id, payload=payload)


@router.patch("/users/{user_id}/password", response_model=AdminActionResponse)
async def update_user_password(
    user_id: int,
    payload: UserPasswordUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.update_user_password(db=db, user_id=user_id, payload=payload)


@router.patch("/users/{user_id}/status", response_model=EmployeeAccountResponse)
async def update_user_status(
    user_id: int,
    payload: UserStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.update_user_status(db=db, user_id=user_id, payload=payload)
