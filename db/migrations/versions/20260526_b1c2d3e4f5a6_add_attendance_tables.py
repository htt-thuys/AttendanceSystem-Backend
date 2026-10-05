"""add attendance tables

Revision ID: b1c2d3e4f5a6
Revises: c4a51d9137aa
Create Date: 2026-05-26 09:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5a6"
down_revision = "25b7d3c8a4e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "work_schedules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("late_threshold_minutes", sa.Integer(), nullable=False, server_default=sa.text("15")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.alter_column("work_schedules", "late_threshold_minutes", server_default=None)
    op.alter_column("work_schedules", "is_default", server_default=None)

    op.create_table(
        "attendance_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("employee_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_out_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("check_in_log_id", sa.Integer(), nullable=True),
        sa.Column("check_out_log_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'absent'")),
        sa.Column("work_hours", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["check_in_log_id"], ["recognition_logs.id"]),
        sa.ForeignKeyConstraint(["check_out_log_id"], ["recognition_logs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
    )
    op.alter_column("attendance_records", "status", server_default=None)

    op.create_index("ix_attendance_date", "attendance_records", ["date"], unique=False)
    op.create_index(
        "ix_attendance_employee_date",
        "attendance_records",
        ["employee_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_attendance_employee_date", table_name="attendance_records")
    op.drop_index("ix_attendance_date", table_name="attendance_records")
    op.drop_table("attendance_records")
    op.drop_table("work_schedules")
