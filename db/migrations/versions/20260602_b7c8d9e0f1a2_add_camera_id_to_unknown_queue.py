"""add camera_id to unknown_queue

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-02 15:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c8d9e0f1a2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("unknown_queue", sa.Column("camera_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_unknown_queue_camera_id",
        "unknown_queue",
        "cameras",
        ["camera_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_unknown_queue_camera_id", "unknown_queue", type_="foreignkey")
    op.drop_column("unknown_queue", "camera_id")
