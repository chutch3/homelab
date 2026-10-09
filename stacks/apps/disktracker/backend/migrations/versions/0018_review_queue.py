"""Scraped offers that cannot be matched (no MPN, unmapped condition, capacity problems)
wait in a review queue, one entry per source URL."""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "unmatched",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("retailer", sa.String(20), nullable=False),
        sa.Column("seller", sa.String(120), nullable=False),
        sa.Column("mpn", sa.String(100)),
        sa.Column("condition", sa.String(40)),
        sa.Column("capacity_tb", sa.Numeric(8, 2)),
        sa.Column("item_price_cents", sa.Integer()),
        sa.Column("shipping_cents", sa.Integer()),
        sa.Column("in_stock", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.String(40), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("uq_unmatched_source_url", "unmatched", ["source", "url"], unique=True)


def downgrade() -> None:
    op.drop_table("unmatched")
