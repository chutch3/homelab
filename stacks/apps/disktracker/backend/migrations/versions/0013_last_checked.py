"""An unchanged price is not stored again; the offer records when it was last checked."""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("last_checked_at", sa.DateTime(timezone=True)))


def downgrade() -> None:
    op.drop_column("listings", "last_checked_at")
