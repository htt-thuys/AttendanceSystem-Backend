from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import parse_token_data
from infrastructure.database.models import User
from infrastructure.database.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Lấy user hiện tại từ Bearer token, kiểm tra token hợp lệ và tài khoản còn hoạt động."""
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thiếu Bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_data = parse_token_data(credentials.credentials)
    if not token_data or (token_data.user_id is None and not token_data.username):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if token_data.user_id is not None:
        query = select(User).where(User.id == token_data.user_id)
    else:
        query = select(User).where(User.username == token_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

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

    return user


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """Tạo dependency kiểm tra user hiện tại có thuộc một trong các role được phép hay không."""

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền truy cập chức năng này",
            )
        return current_user

    return dependency
