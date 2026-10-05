from sqlalchemy import and_, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Employee, FaceVector, RecognitionLog


async def list_employee_records(
    db: AsyncSession,
    status: str | None = None,
) -> list[tuple[Employee, int]]:
    query = (
        select(
            Employee,
            func.count(FaceVector.id).label("vector_count"),
        )
        .outerjoin(
            FaceVector,
            and_(FaceVector.employee_id == Employee.id, FaceVector.is_active.is_(True)),
        )
        .group_by(Employee.id)
        .order_by(Employee.created_at.desc())
    )
    if status:
        query = query.where(Employee.status == status)
    else:
        query = query.where(Employee.status != "deleted")

    result = await db.execute(query)
    return list(result.all())


async def get_employee_record(
    db: AsyncSession,
    emp_id: int,
    include_deleted: bool = False,
) -> Employee | None:
    query = select(Employee).where(Employee.id == emp_id)
    if not include_deleted:
        query = query.where(Employee.status != "deleted")
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_employee_vector_records(
    db: AsyncSession,
    emp_id: int,
    include_inactive: bool = False,
) -> list[FaceVector]:
    query = select(FaceVector).where(FaceVector.employee_id == emp_id)
    if not include_inactive:
        query = query.where(FaceVector.is_active.is_(True))
    query = query.order_by(FaceVector.created_at.desc(), FaceVector.id.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_employee_vector_record(db: AsyncSession, emp_id: int, vec_id: int) -> FaceVector | None:
    query = select(FaceVector).where(
        FaceVector.id == vec_id,
        FaceVector.employee_id == emp_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_employee_record(
    db: AsyncSession,
    full_name: str,
    employee_code: str,
    avatar_path: str | None,
) -> Employee:
    employee = Employee(
        full_name=full_name,
        employee_code=employee_code,
        avatar_path=avatar_path,
    )
    db.add(employee)
    await db.flush()
    return employee


async def create_face_vector_record(
    db: AsyncSession,
    employee_id: int,
    source: str | None,
    source_image_path: str,
    quality_score: float | None,
    score_at_create: float | None,
) -> FaceVector:
    face_vector = FaceVector(
        employee_id=employee_id,
        qdrant_point_id=0,
        source=source,
        source_image_path=source_image_path,
        quality_score=quality_score,
        score_at_create=score_at_create,
        is_active=True,
    )
    db.add(face_vector)
    await db.flush()
    return face_vector


async def delete_face_vectors_by_employee_id(db: AsyncSession, employee_id: int) -> None:
    await db.execute(delete(FaceVector).where(FaceVector.employee_id == employee_id))


async def list_recognition_logs_by_employee_id(db: AsyncSession, employee_id: int) -> list[RecognitionLog]:
    query = select(RecognitionLog).where(RecognitionLog.employee_id == employee_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def clear_employee_links_in_logs(db: AsyncSession, employee_id: int) -> None:
    query = select(RecognitionLog).where(RecognitionLog.employee_id == employee_id)
    result = await db.execute(query)
    for log_entry in result.scalars().all():
        log_entry.employee_id = None
