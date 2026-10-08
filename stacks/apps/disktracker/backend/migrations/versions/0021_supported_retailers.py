"""Only retailers disktracker collects from stay retailers; the rest (entered by hand) become
Other, named after the store and any marketplace seller: eBay / Beach Audio becomes Other
"eBay · Beach Audio"."""

import sqlalchemy as sa
from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None

RETIRED = {
    "newegg": "Newegg",
    "amazon": "Amazon",
    "ebay": "eBay",
    "bhphoto": "B&H",
    "bestbuy": "Best Buy",
}
SEPARATOR = " · "


def upgrade() -> None:
    for retailer, name in RETIRED.items():
        op.execute(
            sa.text(
                "UPDATE listings SET retailer = 'other', seller = CASE WHEN seller = ''"
                " THEN :name ELSE :name || :separator || seller END WHERE retailer = :retailer"
            ).bindparams(name=name, separator=SEPARATOR, retailer=retailer)
        )


def downgrade() -> None:
    for retailer, name in RETIRED.items():
        op.execute(
            sa.text(
                "UPDATE listings SET retailer = :retailer, seller = CASE WHEN seller = :name"
                " THEN '' ELSE substr(seller, length(:prefix) + 1) END"
                " WHERE retailer = 'other' AND (seller = :name OR seller LIKE :pattern)"
            ).bindparams(
                retailer=retailer,
                name=name,
                prefix=name + SEPARATOR,
                pattern=name.replace("%", r"\%").replace("_", r"\_") + SEPARATOR + "%",
            )
        )
