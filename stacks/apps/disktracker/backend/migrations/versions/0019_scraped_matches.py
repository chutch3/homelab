"""Remember how a reviewer resolved (or ignored) a scraped source URL, so later scrapes
of it are recorded directly instead of re-queued."""

import sqlalchemy as sa
from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scraped_matches",
        sa.Column("source", sa.String(40), primary_key=True),
        sa.Column("url", sa.Text(), primary_key=True),
        sa.Column("mpn", sa.String(100)),
        sa.Column("condition", sa.String(40)),
        sa.Column("ignored", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_table("scraped_matches")
