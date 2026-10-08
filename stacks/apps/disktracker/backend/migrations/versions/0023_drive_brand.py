"""A drive's maker (Seagate, Western Digital…), as a collector names it; unknown until then."""

import sqlalchemy as sa
from alembic import op

revision = "0023"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("drives", sa.Column("brand", sa.String(60), nullable=True))


def downgrade() -> None:
    op.drop_column("drives", "brand")
