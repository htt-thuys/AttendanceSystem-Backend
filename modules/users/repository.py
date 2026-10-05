from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database.models import Employee, User


async def get_user_by_employee_id(db: AsyncSession, employee_id: int) -> User | None:
    query = (
        select(User)
        .join(Employee, Employee.id == User.employee_id)
        .where(
            User.employee_id == employee_id,
            Employee.status != "deleted",
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    query = (
        select(User)
        .outerjoin(Employee, Employee.id == User.employee_id)
        .where(
            User.id == user_id,
            or_(User.employee_id.is_(None), Employee.status != "deleted"),
        )
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user_record(
    db: AsyncSession,
    username: str,
    email: str | None,
    password_hash: str,
    role: str,
    employee_id: int | None,
) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=password_hash,
        role=role,
        is_active=True,
        employee_id=employee_id,
    )
    db.add(user)
    await db.flush()
    return user
