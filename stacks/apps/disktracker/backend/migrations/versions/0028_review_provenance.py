"""Who submitted an offer that waits for review, so that resolving it records the price as theirs.
Until now only collectors queued offers."""

import sqlalchemy as sa
from alembic import op

revision = "0028"
down_revision = "0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "unmatched",
        sa.Column("provenance", sa.String(40), nullable=False, server_default="collected"),
    )
    op.alter_column("unmatched", "provenance", server_default=None)


def downgrade() -> None:
    op.drop_column("unmatched", "provenance")
