from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from core.config import settings
from modules.auth.schemas import TokenData

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash password bằng bcrypt."""
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Xác minh plain password với bcrypt hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_token(data: dict, expires_delta: timedelta, token_type: str) -> str:
    """Tạo JWT token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire, "type": token_type})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT access token."""
    return create_token(
        data=data,
        expires_delta=expires_delta
        or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT refresh token."""
    return create_token(
        data=data,
        expires_delta=expires_delta or timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def decode_token(token: str) -> Optional[dict]:
    """Giải mã JWT token. Trả về None nếu invalid."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None


def parse_token_data(token: str) -> Optional[TokenData]:
    """Chuyển JWT token thành dữ liệu người dùng tối thiểu để dùng cho dependency auth."""
    payload = decode_token(token)
    if not payload:
        return None
    if payload.get("type", "access") != "access":
        return None

    employee_id = payload.get("employee_id")
    user_id = payload.get("user_id")
    return TokenData(
        username=payload.get("sub"),
        user_id=int(user_id) if user_id not in (None, "") else None,
        role=payload.get("role"),
        employee_id=int(employee_id) if employee_id not in (None, "") else None,
    )
