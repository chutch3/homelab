"""Every store offers are recorded under is a source: how the collector reads it (or that it
is entered by hand), when, and on what basis. An offer's store is its source's key, and a
queued scraped offer names only its source. Condition rules say which text names which
condition, in order.

The three stores the collector had built in become sources that read them as before, Other
becomes a store entered by hand, and so does any other store offers were recorded under."""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0024"
down_revision = "0023"
branch_labels = None
depends_on = None

SCHEDULE = "0 */8 * * *"
SEEDED = [
    {
        "key": "serverpartdeals", "name": "ServerPartDeals", "kind": "shopify",
        "base_url": "https://www.serverpartdeals.com",
        "settings": {
            "collections": ["hard-drives", "solid-state-drives"], "free_shipping": True,
        },
        # Its terms of service forbid automated access; permission has been asked for.
        "basis": "unconfirmed",
    },
    {
        "key": "goharddrive", "name": "goHardDrive", "kind": "sitemap",
        "base_url": "https://www.goharddrive.com",
        "settings": {
            "sitemap_path": "", "product_path_pattern": "-p/",
            "free_shipping_marker": "Help_FreeShipping",
        },
        "basis": "terms_allow",
    },
    {
        "key": "westerndigital", "name": "Western Digital", "kind": "sap_commerce",
        "base_url": "https://www.westerndigital.com",
        "settings": {
            "api_url": "https://api.westerndigital.com/wdwebservices/v2", "site": "us",
            # Its robots.txt names an index of every locale's sitemaps.
            "sitemap_path": "/products-sitemap.xml",
            "product_path_pattern": "^/products/(recertified/)?internal-drives/",
            "recertified_sku_prefix": "R",
        },
        "basis": "terms_allow",
    },
    {
        "key": "other", "name": "Other", "kind": "manual", "base_url": "", "settings": {},
        "basis": "unconfirmed",
    },
]  # fmt: skip
# The phrases the readers knew, longest first as they were read.
CONDITION_RULES = [
    (r"\bmanufacturer recertified\b", "manufacturer_recertified"),
    (r"\bseller refurbished\b", "refurbished"),
    (r"\bopen box\b", "used"),
    (r"\brecertified\b", "refurbished"),
    (r"\brefurbished\b", "refurbished"),
    (r"\brenewed\b", "refurbished"),
    (r"\bused\b", "used"),
    (r"\bnew\b", "new"),
]


def upgrade() -> None:
    sources = op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("key", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("settings", JSONB(), nullable=False, server_default="{}"),
        sa.Column("base_url", sa.Text(), nullable=False),
        sa.Column("schedule", sa.String(100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("transport", sa.String(20), nullable=False, server_default="direct"),
        sa.Column("basis", sa.String(20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("run_requested_at", sa.DateTime(timezone=True)),
    )
    connection = op.get_bind()
    # Any other store offers were recorded under, or read from, is one entered by hand.
    recorded = connection.execute(
        sa.text("SELECT retailer FROM listings UNION SELECT source FROM unmatched")
    ).scalars()
    seeded = {source["key"] for source in SEEDED}
    others = [
        {"key": key, "name": key, "kind": "manual", "base_url": "", "settings": {},
         "basis": "unconfirmed"}
        for key in sorted(set(recorded) - seeded)
    ]  # fmt: skip
    op.bulk_insert(
        sources,
        [
            {"id": uuid.uuid4(), "schedule": SCHEDULE, "enabled": True, "transport": "direct",
             "notes": "", **source}
            for source in [*SEEDED, *others]
        ],
    )  # fmt: skip
    op.alter_column("listings", "retailer", new_column_name="store", type_=sa.String(40))
    op.create_foreign_key("fk_listings_source", "listings", "sources", ["store"], ["key"])
    op.drop_column("unmatched", "retailer")
    op.create_foreign_key("fk_unmatched_source", "unmatched", "sources", ["source"], ["key"])
    rules = op.create_table(
        "condition_rules",
        sa.Column("position", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("pattern", sa.Text(), nullable=False),
        sa.Column("condition", sa.String(40), nullable=False),
    )
    op.bulk_insert(
        rules,
        [
            {"position": position, "pattern": pattern, "condition": condition}
            for position, (pattern, condition) in enumerate(CONDITION_RULES)
        ],
    )


def downgrade() -> None:
    op.drop_table("condition_rules")
    op.drop_constraint("fk_unmatched_source", "unmatched", type_="foreignkey")
    op.add_column("unmatched", sa.Column("retailer", sa.String(40)))
    op.execute("UPDATE unmatched SET retailer = source")
    op.alter_column("unmatched", "retailer", nullable=False)
    op.drop_constraint("fk_listings_source", "listings", type_="foreignkey")
    # Keys can be longer than the 20 characters the retailer columns had.
    op.alter_column("listings", "store", new_column_name="retailer")
    op.drop_table("sources")
