"""What a reviewer decided a listing is names the drive it was decided to be, not an MPN: a drive
merged into another takes the decisions with it, and one that is removed takes its own away (its
pages are judged again from what they say next).

A decision is converted to the drive its MPN names now, as its own MPN or another of its MPNs.
One whose MPN no drive goes by is not guessed at: it is retired whole to retired_page_decisions,
and named, as 0037 retired the decisions it could not place."""

import sys

import sqlalchemy as sa
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scraped_matches",
        sa.Column(
            "drive_id",
            sa.Uuid(),
            sa.ForeignKey("drives.id", name="fk_scraped_matches_drive", ondelete="CASCADE"),
        ),
    )
    op.execute(
        "UPDATE scraped_matches m SET drive_id = coalesce("
        " (SELECT d.id FROM drives d WHERE d.mpn = m.mpn),"
        " (SELECT a.drive_id FROM mpn_aliases a WHERE a.alias = m.mpn))"
        " WHERE m.mpn IS NOT NULL"
    )
    unplaced = "m.mpn IS NOT NULL AND m.drive_id IS NULL"
    retired = op.get_bind().execute(sa.text(
        "INSERT INTO retired_page_decisions (source, url, mpn, condition, ignored)"
        f" SELECT m.source, m.url, m.mpn, m.condition, m.ignored FROM scraped_matches m"
        f" WHERE {unplaced} RETURNING source, url, mpn"
    )).all()  # fmt: skip
    for source, url, mpn in retired:
        # Shown where the upgrade runs (the backend's start); kept in retired_page_decisions.
        print(f"Retired the decision of {source} {url}: no drive goes by {mpn}.", file=sys.stderr)
    op.execute(f"DELETE FROM scraped_matches m WHERE {unplaced}")
    op.drop_column("scraped_matches", "mpn")


def downgrade() -> None:
    op.add_column("scraped_matches", sa.Column("mpn", sa.String(100)))
    op.execute("UPDATE scraped_matches m SET mpn = d.mpn FROM drives d WHERE d.id = m.drive_id")
    op.drop_column("scraped_matches", "drive_id")
