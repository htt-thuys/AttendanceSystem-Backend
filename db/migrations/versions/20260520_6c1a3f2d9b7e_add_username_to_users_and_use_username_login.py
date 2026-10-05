"""add username to users and use username login

Revision ID: 6c1a3f2d9b7e
Revises: c4a51d9137aa
Create Date: 2026-05-20 10:45:00.000000
"""

from collections import Counter

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6c1a3f2d9b7e"
down_revision = "c4a51d9137aa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(length=50), nullable=True))
    op.alter_column("users", "email", existing_type=sa.Text(), nullable=True)

    bind = op.get_bind()
    users = list(
        bind.execute(
            sa.text("SELECT id, email FROM users ORDER BY id ASC")
        ).mappings()
    )
    usernames = _build_unique_usernames(users)

    for user_id, username in usernames.items():
        bind.execute(
            sa.text("UPDATE users SET username = :username WHERE id = :user_id"),
            {"username": username, "user_id": user_id},
        )

    op.alter_column("users", "username", existing_type=sa.String(length=50), nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])


def downgrade() -> None:
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.alter_column("users", "email", existing_type=sa.Text(), nullable=False)
    op.drop_column("users", "username")


def _build_unique_usernames(users: list[dict]) -> dict[int, str]:
    """Tạo username duy nhất cho toàn bộ user hiện có dựa trên email hoặc id."""
    base_names: dict[int, str] = {}
    used_counter: Counter[str] = Counter()

    for row in users:
        user_id = row["id"]
        email = row["email"] or ""
        base_name = _normalize_username(email.split("@")[0] if "@" in email else email)
        if not base_name:
            base_name = f"user{user_id}"
        base_names[user_id] = base_name
        used_counter[base_name] += 1

    assigned: set[str] = set()
    result: dict[int, str] = {}

    for row in users:
        user_id = row["id"]
        base_name = base_names[user_id]
        username = base_name
        if username in assigned:
            username = f"{base_name}_{user_id}"
        while username in assigned:
            username = f"{username}_{user_id}"
        assigned.add(username)
        result[user_id] = username

    return result


def _normalize_username(raw_value: str) -> str:
    """Chuẩn hóa username về dạng đơn giản chỉ gồm chữ, số, gạch dưới và dấu chấm."""
    cleaned = []
    for char in raw_value.strip().lower():
        if char.isalnum() or char in {"_", "."}:
            cleaned.append(char)
        elif char in {" ", "-"}:
            cleaned.append("_")
    return "".join(cleaned).strip("_.")
