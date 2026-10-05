from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from infrastructure.database.models import Employee, User
from infrastructure.database.session import get_db
from modules.auth.schemas import LoginRequest, RefreshTokenRequest, Token

router = APIRouter()


def _build_token_payload(user: User) -> dict:
    return {
        "sub": user.username,
        "user_id": str(user.id),
        "role": user.role,
        "employee_id": str(user.employee_id) if user.employee_id else None,
    }


async def _get_login_allowed_user(
    db: AsyncSession,
    username: str | None = None,
    user_id: int | None = None,
) -> User | None:
    query = select(User).outerjoin(Employee, Employee.id == User.employee_id)
    if user_id is not None:
        query = query.where(User.id == user_id)
    elif username is not None:
        query = query.where(User.username == username)
    else:
        return None

    query = query.where(
        or_(User.employee_id.is_(None), Employee.status != "deleted"),
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await _get_login_allowed_user(db, username=login_data.username)

    if not user or not verify_password(login_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Username hoặc mật khẩu không chính xác",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đang bị vô hiệu hóa",
        )

    token_payload = _build_token_payload(user)
    access_token = create_access_token(data=token_payload)
    refresh_token = create_refresh_token(data=token_payload)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(refresh_data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    try:
        parsed_user_id = int(user_id) if user_id not in (None, "") else None
    except (TypeError, ValueError):
        parsed_user_id = None

    user = await _get_login_allowed_user(db, user_id=parsed_user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tài khoản không tồn tại",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản đang bị vô hiệu hóa",
        )

    token_payload = _build_token_payload(user)
    access_token = create_access_token(data=token_payload)
    new_refresh_token = create_refresh_token(data=token_payload)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer",
    }
