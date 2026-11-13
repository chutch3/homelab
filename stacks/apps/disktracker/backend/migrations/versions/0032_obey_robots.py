"""Whether a source obeys robots.txt: every source does, as before, until it is told not to,
which only a source collected with the store's permission may be."""

import sqlalchemy as sa
from alembic import op

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sources",
        sa.Column("obey_robots", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("sources", "obey_robots")
