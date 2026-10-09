"""Manual listings and observed prices."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "listings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("description", sa.String(160), nullable=False),
        sa.Column("model", sa.String(100)),
        sa.Column("seller", sa.String(120), nullable=False),
        sa.Column("url", sa.Text()),
        sa.Column("capacity_tb", sa.Numeric(8, 2), nullable=False),
        sa.Column("condition", sa.String(40), nullable=False),
        sa.CheckConstraint("capacity_tb > 0", name="positive_capacity"),
    )
    op.create_table(
        "observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id"), nullable=False),
        sa.Column("item_price_cents", sa.Integer()),
        sa.Column("shipping_cents", sa.Integer()),
        sa.Column("fee_cents", sa.Integer()),
        sa.Column("availability", sa.String(20), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "item_price_cents >= 0 AND shipping_cents >= 0 AND fee_cents >= 0",
            name="nonnegative_costs",
        ),
    )
    op.create_index(
        "observations_listing_time", "observations", ["listing_id", "observed_at", "entered_at"]
    )


def downgrade() -> None:
    op.drop_table("observations")
    op.drop_table("listings")
