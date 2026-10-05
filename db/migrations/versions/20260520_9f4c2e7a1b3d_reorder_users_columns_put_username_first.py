"""reorder users columns put username first

Revision ID: 9f4c2e7a1b3d
Revises: 6c1a3f2d9b7e
Create Date: 2026-05-20 11:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "9f4c2e7a1b3d"
down_revision = "6c1a3f2d9b7e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    user_fk_constraints = _load_user_fk_constraints(bind)

    _drop_user_fk_constraints(bind, user_fk_constraints)
    _create_users_reordered_table()
    _copy_users_data_upgrade(bind)
    op.drop_table("users")
    op.rename_table("users_reordered", "users")
    _rename_users_reordered_sequence(bind, old_name="users_reordered_id_seq", new_name="users_id_seq")
    _sync_users_sequence(bind)
    _recreate_user_fk_constraints(bind, user_fk_constraints)


def downgrade() -> None:
    bind = op.get_bind()
    user_fk_constraints = _load_user_fk_constraints(bind)

    _drop_user_fk_constraints(bind, user_fk_constraints)
    _create_users_original_order_table()
    _copy_users_data_downgrade(bind)
    op.drop_table("users")
    op.rename_table("users_original_order", "users")
    _rename_users_reordered_sequence(bind, old_name="users_original_order_id_seq", new_name="users_id_seq")
    _sync_users_sequence(bind)
    _recreate_user_fk_constraints(bind, user_fk_constraints)


def _create_users_reordered_table() -> None:
    """Tạo bảng users tạm với thứ tự cột mới: id, username, email, password_hash, ..."""
    op.create_table(
        "users_reordered",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )


def _create_users_original_order_table() -> None:
    """Tạo bảng users tạm với thứ tự cột cũ để phục vụ downgrade."""
    op.create_table(
        "users_original_order",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )


def _copy_users_data_upgrade(bind) -> None:
    """Copy toàn bộ dữ liệu users sang bảng tạm theo thứ tự cột mới."""
    bind.execute(
        sa.text(
            """
            INSERT INTO users_reordered (id, username, email, password_hash, role, is_active, employee_id, created_at)
            SELECT id, username, email, password_hash, role, is_active, employee_id, created_at
            FROM users
            ORDER BY id ASC
            """
        )
    )


def _copy_users_data_downgrade(bind) -> None:
    """Copy toàn bộ dữ liệu users sang bảng tạm theo thứ tự cột cũ."""
    bind.execute(
        sa.text(
            """
            INSERT INTO users_original_order (id, email, password_hash, role, employee_id, created_at, is_active, username)
            SELECT id, email, password_hash, role, employee_id, created_at, is_active, username
            FROM users
            ORDER BY id ASC
            """
        )
    )


def _load_user_fk_constraints(bind) -> list[dict]:
    """Lấy danh sách foreign key đang trỏ vào bảng users để drop rồi tạo lại sau khi rebuild."""
    return list(
        bind.execute(
            sa.text(
                """
                SELECT
                    conname,
                    conrelid::regclass::text AS table_name,
                    pg_get_constraintdef(oid) AS definition
                FROM pg_constraint
                WHERE contype = 'f'
                  AND confrelid = 'users'::regclass
                ORDER BY conname ASC
                """
            )
        ).mappings()
    )


def _drop_user_fk_constraints(bind, constraints: list[dict]) -> None:
    """Xóa tạm các foreign key đang trỏ vào users để có thể rebuild bảng."""
    for constraint in constraints:
        bind.execute(
            sa.text(
                f'ALTER TABLE "{constraint["table_name"]}" DROP CONSTRAINT "{constraint["conname"]}"'
            )
        )


def _recreate_user_fk_constraints(bind, constraints: list[dict]) -> None:
    """Tạo lại các foreign key đã drop sau khi bảng users mới sẵn sàng."""
    for constraint in constraints:
        bind.execute(
            sa.text(
                f'ALTER TABLE "{constraint["table_name"]}" '
                f'ADD CONSTRAINT "{constraint["conname"]}" {constraint["definition"]}'
            )
        )


def _rename_users_reordered_sequence(bind, old_name: str, new_name: str) -> None:
    """Đổi tên sequence id của bảng tạm về tên chuẩn users_id_seq nếu sequence tồn tại."""
    sequence_exists = bind.execute(
        sa.text("SELECT to_regclass(:sequence_name)"),
        {"sequence_name": old_name},
    ).scalar()
    if sequence_exists:
        bind.execute(sa.text(f'ALTER SEQUENCE "{old_name}" RENAME TO "{new_name}"'))


def _sync_users_sequence(bind) -> None:
    """Đồng bộ sequence users_id_seq với id lớn nhất hiện có trong bảng users."""
    bind.execute(
        sa.text(
            """
            SELECT setval(
                'users_id_seq',
                COALESCE((SELECT MAX(id) FROM users), 1),
                true
            )
            """
        )
    )
