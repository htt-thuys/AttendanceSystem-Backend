"""
db/migrations/env.py — Alembic environment config.
Load DATABASE_URL từ .env và dùng synchronous driver để chạy migration.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import toàn bộ models để Alembic autogenerate nhận diện đủ bảng
from infrastructure.database.models import Base  # noqa: F401

# --- Alembic Config ---
config = context.config

# Logging từ alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata để autogenerate
target_metadata = Base.metadata


def get_url() -> str:
    """
    Đọc DATABASE_URL từ .env và chuyển sang sync driver (psycopg2)
    vì Alembic không hỗ trợ asyncpg trực tiếp khi chạy migration.
    """
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("DATABASE_URL", "")
    # Alembic cần synchronous driver: đổi asyncpg → psycopg2
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def run_migrations_offline() -> None:
    """Chạy migration ở chế độ offline (không cần kết nối thật)."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Chạy migration ở chế độ online (kết nối thật đến PostgreSQL)."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
