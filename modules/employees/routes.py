from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_roles
from infrastructure.database.session import get_db
from modules.admin.schemas import (
    AdminActionResponse,
    EmployeeListItemResponse,
    EmployeeVectorItemResponse,
    RecognitionLogItemResponse,
)
from modules.employees import service
from modules.recognition_logs import service as recognition_logs_service

router = APIRouter()


@router.get("/employees/active-public", response_model=list[EmployeeListItemResponse])
async def get_active_public_employee_list(
    db: AsyncSession = Depends(get_db),
):
    return await service.list_active_public_employees(db=db)


@router.get("/employees", response_model=list[EmployeeListItemResponse])
async def get_employee_list(
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await service.list_employees(db=db, status_filter=status)


@router.post("/employees", response_model=AdminActionResponse)
async def create_employee(
    full_name: str = Form(...),
    employee_code: str = Form(...),
    avatar: UploadFile = File(...),
    vector_images: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    success, employee_id = await service.create_employee(
        db=db,
        full_name=full_name,
        employee_code=employee_code,
        avatar=avatar,
        vector_images=vector_images,
    )
    return AdminActionResponse(success=success, employee_id=employee_id)


@router.delete("/employees/{emp_id}", response_model=AdminActionResponse)
async def deactivate_employee(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.deactivate_employee(db=db, emp_id=emp_id)


@router.post("/employees/{emp_id}/reactivate", response_model=AdminActionResponse)
async def reactivate_employee(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.reactivate_employee(db=db, emp_id=emp_id)


@router.post("/employees/{emp_id}/anonymize", response_model=AdminActionResponse)
async def anonymize_employee(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.anonymize_employee(db=db, emp_id=emp_id)


@router.patch("/employees/{emp_id}/avatar", response_model=AdminActionResponse)
async def update_employee_avatar(
    emp_id: int,
    avatar: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    await service.update_employee_avatar(db=db, emp_id=emp_id, avatar=avatar)
    return AdminActionResponse(success=True)


@router.post("/employees/{emp_id}/vectors", response_model=AdminActionResponse)
async def add_employee_vectors(
    emp_id: int,
    vector_images: list[UploadFile] | None = File(None),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    await service.add_employee_vectors(
        db=db,
        emp_id=emp_id,
        vector_images=vector_images,
    )
    return AdminActionResponse(success=True)


@router.get("/employees/{emp_id}/vectors", response_model=list[EmployeeVectorItemResponse])
async def get_employee_vectors(
    emp_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    return await service.list_employee_vectors(db=db, emp_id=emp_id)


@router.delete("/employees/{emp_id}/vectors/{vec_id}", response_model=AdminActionResponse)
async def delete_vector(
    emp_id: int,
    vec_id: int,
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin")),
):
    await service.delete_employee_vector(db=db, emp_id=emp_id, vec_id=vec_id)
    return AdminActionResponse(success=True)


@router.get("/employees/{emp_id}/recognition-logs", response_model=list[RecognitionLogItemResponse])
async def get_employee_recognition_logs(
    emp_id: int,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_roles("admin", "reviewer")),
):
    return await recognition_logs_service.list_employee_recognition_logs(
        db=db,
        emp_id=emp_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
