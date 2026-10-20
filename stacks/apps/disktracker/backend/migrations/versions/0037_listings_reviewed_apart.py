"""Review by listing: what one store page says one offer is, before anyone trusts it (its store,
page, seller, and the MPN and condition it gives, blank where it gives none). Two offers of one
page wait for review, and are decided, each on its own.

- unmatched: unique by listing instead of by page, and keeping what the page said of the drive
  (its other MPNs, brand and specifications). NULL in those means it was not kept, as for every
  item queued before now: nothing is made up for them.
- scraped_matches: a decision is of one listing, and keeps the title it was made on. What a page
  said when the decisions made before now were taken was never kept, so they cannot be told
  apart by listing. They are retired, not guessed at: moved whole to retired_page_decisions, for
  a person to look through, and no longer applied. Their pages are judged again from what they
  say next.

Queued items keep their ids, so a review decision sent again is answered as it was."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None

LISTING = "source, url, seller, coalesce(mpn, ''), coalesce(condition, '')"


def upgrade() -> None:
    op.drop_index("uq_unmatched_source_url", table_name="unmatched")
    op.execute(f"CREATE UNIQUE INDEX uq_unmatched_listing ON unmatched ({LISTING})")
    op.add_column("unmatched", sa.Column("aliases", JSONB))
    op.add_column("unmatched", sa.Column("brand", sa.String(60)))
    op.add_column("unmatched", sa.Column("specifications", JSONB))

    op.create_table(
        "retired_page_decisions",
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("mpn", sa.String(100)),
        sa.Column("condition", sa.String(40)),
        sa.Column("ignored", sa.Boolean(), nullable=False),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.execute(
        "INSERT INTO retired_page_decisions (source, url, mpn, condition, ignored)"
        " SELECT source, url, mpn, condition, ignored FROM scraped_matches"
    )
    op.execute("DELETE FROM scraped_matches")
    op.drop_constraint("scraped_matches_pkey", "scraped_matches", type_="primary")
    for name, width in (("seller", 120), ("read_mpn", 100), ("read_condition", 40)):
        op.add_column(
            "scraped_matches",
            sa.Column(name, sa.String(width), nullable=False, server_default=""),
        )
    op.add_column("scraped_matches", sa.Column("reviewed_title", sa.String(160)))
    op.create_primary_key(
        "scraped_matches_pkey",
        "scraped_matches",
        ["source", "url", "seller", "read_mpn", "read_condition"],
    )


def downgrade() -> None:
    # A page holds one decision again: of several listings decided, one is kept.
    op.execute(
        "DELETE FROM scraped_matches m USING scraped_matches o WHERE m.source = o.source"
        " AND m.url = o.url AND (m.seller, m.read_mpn, m.read_condition)"
        " > (o.seller, o.read_mpn, o.read_condition)"
    )
    op.drop_constraint("scraped_matches_pkey", "scraped_matches", type_="primary")
    for name in ("reviewed_title", "read_condition", "read_mpn", "seller"):
        op.drop_column("scraped_matches", name)
    op.create_primary_key("scraped_matches_pkey", "scraped_matches", ["source", "url"])
    op.execute(
        "INSERT INTO scraped_matches (source, url, mpn, condition, ignored)"
        " SELECT DISTINCT ON (source, url) source, url, mpn, condition, ignored"
        " FROM retired_page_decisions ORDER BY source, url"
        " ON CONFLICT (source, url) DO NOTHING"
    )
    op.drop_table("retired_page_decisions")

    for name in ("specifications", "brand", "aliases"):
        op.drop_column("unmatched", name)
    op.drop_index("uq_unmatched_listing", table_name="unmatched")
    op.execute(
        "DELETE FROM unmatched u USING unmatched o WHERE u.source = o.source AND u.url = o.url"
        " AND (u.last_seen_at, u.id) < (o.last_seen_at, o.id)"
    )
    op.create_index("uq_unmatched_source_url", "unmatched", ["source", "url"], unique=True)
