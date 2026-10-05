"""Thêm ảnh nguồn cho từng vector khuôn mặt."""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b4d96c7d1d20"
down_revision: str | None = "4ee0c2034e04"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.add_column(
        "face_vectors",
        sa.Column("source_image_path", sa.Text(), nullable=False, server_default=""),
    )
    op.alter_column("face_vectors", "source_image_path", server_default=None)


def downgrade() -> None:
    op.drop_column("face_vectors", "source_image_path")
