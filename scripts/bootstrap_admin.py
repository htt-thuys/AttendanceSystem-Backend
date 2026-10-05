"""
scripts/bootstrap_admin.py - Tạo hoặc cập nhật tài khoản admin đầu tiên.
"""

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import select

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.security import hash_password
from infrastructure.database.models import User
from infrastructure.database.session import AsyncSessionLocal


async def bootstrap_admin(
    username: str,
    password: str,
    email: str | None,
) -> None:
    """Tạo mới hoặc cập nhật tài khoản admin đầu tiên theo username được truyền vào."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.username == username))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            existing_user.password_hash = hash_password(password)
            existing_user.role = "admin"
            existing_user.is_active = True
            existing_user.email = email
            await session.commit()
            print(f"Đã cập nhật tài khoản admin '{username}'.")
            return

        user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            role="admin",
            is_active=True,
            employee_id=None,
        )
        session.add(user)
        await session.commit()
        print(f"Đã tạo tài khoản admin '{username}'.")


def parse_args() -> argparse.Namespace:
    """Đọc tham số dòng lệnh cho script bootstrap admin."""
    parser = argparse.ArgumentParser(description="Tạo hoặc cập nhật tài khoản admin đầu tiên")
    parser.add_argument("--username", required=True, help="Username đăng nhập của admin")
    parser.add_argument("--password", required=True, help="Mật khẩu đăng nhập của admin")
    parser.add_argument("--email", default=None, help="Email metadata cho admin (optional)")
    return parser.parse_args()


def main() -> None:
    """Chạy script bootstrap admin theo tham số dòng lệnh."""
    args = parse_args()
    asyncio.run(
        bootstrap_admin(
            username=args.username,
            password=args.password,
            email=args.email,
        )
    )


if __name__ == "__main__":
    main()
