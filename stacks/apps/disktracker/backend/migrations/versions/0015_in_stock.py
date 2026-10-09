"""Each price records whether the offer was in stock, so sold-out offers are never
presented as the lowest price."""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "observations",
        sa.Column("in_stock", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("observations", "in_stock")
