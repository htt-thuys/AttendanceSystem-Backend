"""add checkout columns to meeting_participants

Revision ID: a1b2c3d4e5f6
Revises: c2d3e4f5a6b7
Create Date: 2026-05-29 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "meeting_participants",
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "meeting_participants",
        sa.Column("check_out_log_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_meeting_participants_check_out_log_id",
        "meeting_participants",
        "recognition_logs",
        ["check_out_log_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_meeting_participants_check_out_log_id",
        "meeting_participants",
        type_="foreignkey",
    )
    op.drop_column("meeting_participants", "check_out_log_id")
    op.drop_column("meeting_participants", "check_out_time")
