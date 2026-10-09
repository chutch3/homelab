"""Each price records where it came from: "manual" or the collector source that scraped it."""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column("acquisition_method", sa.String(40), nullable=False, server_default="manual"),
    )


def downgrade() -> None:
    op.drop_column("observations", "acquisition_method")
