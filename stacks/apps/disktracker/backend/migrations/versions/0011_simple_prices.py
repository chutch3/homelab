"""Every price has an item price, and shipping and fees are one amount that
defaults to zero, so totals and $/TB are always known."""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM observations WHERE item_price_cents IS NULL")
    op.execute(
        "DELETE FROM listings WHERE NOT EXISTS"
        " (SELECT 1 FROM observations WHERE observations.listing_id = listings.id)"
    )
    op.execute(
        "UPDATE observations SET shipping_cents = coalesce(shipping_cents, 0)"
        " + coalesce(fee_cents, 0)"
    )
    op.alter_column("observations", "item_price_cents", nullable=False)
    op.alter_column("observations", "shipping_cents", nullable=False)
    op.drop_column("observations", "fee_cents")
    op.drop_column("observations", "availability")


def downgrade() -> None:
    op.add_column(
        "observations",
        sa.Column("availability", sa.String(20), nullable=False, server_default="in_stock"),
    )
    op.add_column("observations", sa.Column("fee_cents", sa.Integer(), server_default="0"))
    op.alter_column("observations", "shipping_cents", nullable=True)
    op.alter_column("observations", "item_price_cents", nullable=True)
