"""rename face_score to face_quality in unknown_queue

Revision ID: fa92d3c5b8a1
Revises: b4d96c7d1d20
Create Date: 2026-05-19 11:20:00.000000
"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "fa92d3c5b8a1"
down_revision = "b4d96c7d1d20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("unknown_queue", "face_score", new_column_name="face_quality")


def downgrade() -> None:
    op.alter_column("unknown_queue", "face_quality", new_column_name="face_score")
