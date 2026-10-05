"""add events

Revision ID: d1e2f3a4b5c6
Revises: b7c8d9e0f1a2
Create Date: 2026-06-04 10:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "d1e2f3a4b5c6"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column("events", "is_active", server_default=None)
    op.create_index("ix_events_starts_at", "events", ["starts_at"])
    op.create_index("ix_events_ends_at", "events", ["ends_at"])
    op.create_index("ix_events_active_window", "events", ["is_active", "starts_at", "ends_at"])

    op.add_column("recognition_logs", sa.Column("event_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_recognition_logs_event_id",
        "recognition_logs",
        "events",
        ["event_id"],
        ["id"],
    )
    op.create_index("ix_recognition_logs_event_employee", "recognition_logs", ["event_id", "employee_id"])

    op.add_column("unknown_queue", sa.Column("event_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_unknown_queue_event_id",
        "unknown_queue",
        "events",
        ["event_id"],
        ["id"],
    )
    op.create_index("ix_unknown_queue_event_id", "unknown_queue", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_unknown_queue_event_id", table_name="unknown_queue")
    op.drop_constraint("fk_unknown_queue_event_id", "unknown_queue", type_="foreignkey")
    op.drop_column("unknown_queue", "event_id")

    op.drop_index("ix_recognition_logs_event_employee", table_name="recognition_logs")
    op.drop_constraint("fk_recognition_logs_event_id", "recognition_logs", type_="foreignkey")
    op.drop_column("recognition_logs", "event_id")

    op.drop_index("ix_events_active_window", table_name="events")
    op.drop_index("ix_events_ends_at", table_name="events")
    op.drop_index("ix_events_starts_at", table_name="events")
    op.drop_table("events")
