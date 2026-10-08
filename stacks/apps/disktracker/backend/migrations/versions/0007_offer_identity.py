"""An offer is one retailer selling one MPN in one condition. Conditions are
normalized to four values, and offers that become duplicates are merged."""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE listings SET condition = CASE condition
            WHEN 'seller_refurbished' THEN 'refurbished'
            WHEN 'unknown' THEN 'refurbished'
            WHEN 'open_box' THEN 'used'
            ELSE condition END
        """
    )
    # Keep the offer whose first price is oldest; move every other duplicate's history onto it.
    op.execute(
        """
        CREATE TEMPORARY TABLE offer_merges ON COMMIT DROP AS
        SELECT id, first_value(id) OVER (
            PARTITION BY mpn, seller, condition
            ORDER BY (SELECT min(observed_at) FROM observations WHERE listing_id = listings.id), id
        ) AS keep
        FROM listings WHERE mpn IS NOT NULL
        """
    )
    op.execute("DELETE FROM offer_merges WHERE id = keep")
    op.execute(
        "UPDATE observations SET listing_id = m.keep FROM offer_merges m"
        " WHERE observations.listing_id = m.id"
    )
    op.execute(
        "UPDATE corrections SET listing_id = m.keep FROM offer_merges m"
        " WHERE corrections.listing_id = m.id"
    )
    op.execute(
        "UPDATE listings SET duplicate_of = NULL"
        " WHERE duplicate_of IN (SELECT id FROM offer_merges)"
    )
    op.execute("DELETE FROM listings WHERE id IN (SELECT id FROM offer_merges)")
    op.execute("DROP TABLE offer_merges")
    op.create_index("uq_listings_offer", "listings", ["mpn", "seller", "condition"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_listings_offer", table_name="listings")
