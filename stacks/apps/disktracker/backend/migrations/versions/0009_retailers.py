"""Offers name a retailer from a fixed list; the free-text seller keeps only the
marketplace seller (e.g. an eBay store), so spelling variants stop splitting offers.
Offers entered before MPNs were required get a placeholder MPN and their own drive."""

import uuid

import sqlalchemy as sa
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

KNOWN_RETAILERS = {
    "serverpartdeals": "serverpartdeals",
    "server part deals": "serverpartdeals",
    "goharddrive": "goharddrive",
    "newegg": "newegg",
    "amazon": "amazon",
    "ebay": "ebay",
    "b&h": "bhphoto",
    "b&h photo": "bhphoto",
    "bhphoto": "bhphoto",
    "best buy": "bestbuy",
    "bestbuy": "bestbuy",
}


def retailer_and_seller(text: str) -> tuple[str, str]:
    """'eBay - Beach Audio' -> ('ebay', 'Beach Audio'); unrecognized names become Other."""
    head, _, rest = text.partition(" - ")
    retailer = KNOWN_RETAILERS.get(head.strip().lower())
    return (retailer, rest.strip()) if retailer else ("other", text.strip())


def upgrade() -> None:
    op.add_column(
        "listings", sa.Column("retailer", sa.String(20), nullable=False, server_default="other")
    )
    op.alter_column("listings", "retailer", server_default=None)
    op.drop_index("uq_listings_offer", table_name="listings")
    connection = op.get_bind()
    listings = sa.table(
        "listings",
        sa.column("id", sa.Uuid()),
        sa.column("mpn", sa.String()),
        sa.column("retailer", sa.String()),
        sa.column("seller", sa.String()),
        sa.column("drive_id", sa.Uuid()),
    )
    drives = sa.table("drives", sa.column("id", sa.Uuid()), sa.column("mpn", sa.String()))
    for listing_id, seller in connection.execute(sa.select(listings.c.id, listings.c.seller)).all():
        retailer, marketplace_seller = retailer_and_seller(seller)
        connection.execute(
            sa.update(listings)
            .where(listings.c.id == listing_id)
            .values(retailer=retailer, seller=marketplace_seller)
        )
    for listing_id, mpn in connection.execute(
        sa.select(listings.c.id, listings.c.mpn).where(listings.c.drive_id.is_(None))
    ).all():
        mpn = mpn or f"UNCONFIRMED-{listing_id.hex[:8].upper()}"
        drive_id = connection.execute(
            sa.select(drives.c.id).where(drives.c.mpn == mpn)
        ).scalar_one_or_none()
        if drive_id is None:
            drive_id = uuid.uuid4()
            connection.execute(sa.insert(drives).values(id=drive_id, mpn=mpn))
        connection.execute(
            sa.update(listings)
            .where(listings.c.id == listing_id)
            .values(mpn=mpn, drive_id=drive_id)
        )
    # Keep the offer whose first price is oldest; move every other duplicate's history onto it.
    op.execute(
        """
        CREATE TEMPORARY TABLE offer_merges ON COMMIT DROP AS
        SELECT id, first_value(id) OVER (
            PARTITION BY mpn, retailer, seller, condition
            ORDER BY (SELECT min(observed_at) FROM observations WHERE listing_id = listings.id), id
        ) AS keep
        FROM listings
        """
    )
    op.execute("DELETE FROM offer_merges WHERE id = keep")
    op.execute(
        "UPDATE observations SET listing_id = m.keep FROM offer_merges m"
        " WHERE observations.listing_id = m.id"
    )
    op.execute("DELETE FROM listings WHERE id IN (SELECT id FROM offer_merges)")
    op.execute("DROP TABLE offer_merges")
    op.alter_column("listings", "mpn", nullable=False)
    op.create_index(
        "uq_listings_offer", "listings", ["mpn", "retailer", "seller", "condition"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_listings_offer", table_name="listings")
    op.alter_column("listings", "mpn", nullable=True)
    op.execute(
        "UPDATE listings SET seller = CASE"
        " WHEN retailer = 'other' THEN seller"
        " WHEN seller = '' THEN retailer"
        " ELSE retailer || ' - ' || seller END"
    )
    op.create_index("uq_listings_offer", "listings", ["mpn", "seller", "condition"], unique=True)
    op.drop_column("listings", "retailer")
