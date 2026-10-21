"""An offer is its drive's at a store, from a seller, in a condition: the MPN it was kept under
is its drive's, so it is no longer kept on the offer. Two offers that would then be one are not
merged here: they are named and nothing changes, for a person to settle first."""

import sqlalchemy as sa
from alembic import op

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    clashes = op.get_bind().execute(sa.text(
        "SELECT drive_id, store, seller, condition, string_agg(id::text, ', ' ORDER BY id)"
        " FROM listings GROUP BY drive_id, store, seller, condition HAVING count(*) > 1"
    )).all()  # fmt: skip
    if clashes:
        named = "; ".join(
            f"drive {d} at {s}/{seller or '-'} {c}: {ids}" for d, s, seller, c, ids in clashes
        )
        raise RuntimeError(f"Offers that would be one, to settle before upgrading: {named}")
    op.create_index(
        "uq_listings_drive_offer", "listings", ["drive_id", "store", "seller", "condition"],
        unique=True,
    )  # fmt: skip
    op.drop_index("uq_listings_offer", table_name="listings")
    op.drop_column("listings", "mpn")


def downgrade() -> None:
    op.add_column("listings", sa.Column("mpn", sa.String(100)))
    op.execute(
        "UPDATE listings SET mpn = drives.mpn FROM drives WHERE drives.id = listings.drive_id"
    )
    # The trend revision's deferred triggers fire now: a table with events pending cannot change.
    op.execute("SET CONSTRAINTS ALL IMMEDIATE")
    op.alter_column("listings", "mpn", nullable=False)
    op.create_index(
        "uq_listings_offer", "listings", ["mpn", "store", "seller", "condition"], unique=True
    )
    op.drop_index("uq_listings_drive_offer", table_name="listings")
