"""Rename listing description/model to title/mpn to match what each value is."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("listings", "description", new_column_name="title")
    op.alter_column("listings", "model", new_column_name="mpn")


def downgrade() -> None:
    op.alter_column("listings", "mpn", new_column_name="model")
    op.alter_column("listings", "title", new_column_name="description")
