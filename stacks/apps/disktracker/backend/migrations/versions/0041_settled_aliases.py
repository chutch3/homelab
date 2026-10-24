"""What a reviewer accepted of a listing includes the MPNs another drive goes by its page named:
settled, so the same page collected again is taken as decided, and only an MPN no reviewer has
accepted it naming opens review again."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scraped_matches",
        sa.Column("settled_aliases", ARRAY(sa.String(100)), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("scraped_matches", "settled_aliases")
