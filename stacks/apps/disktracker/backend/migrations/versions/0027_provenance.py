"""Who submitted each price, apart from where it was seen: a person or a collector. A collected
price used to carry its source's key here, which is the store of the offer it belongs to.

Going back is approximate: the key each price had is not kept, so a collected price is given its
offer's store as it is now. That is the key it had unless the price was recorded under another
source's key than its offer's store."""

from alembic import op

revision = "0027"
down_revision = "0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "UPDATE observations SET acquisition_method = 'collected'"
        " WHERE acquisition_method <> 'manual'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE observations SET acquisition_method = listings.store FROM listings"
        " WHERE listings.id = observations.listing_id"
        " AND observations.acquisition_method = 'collected'"
    )
