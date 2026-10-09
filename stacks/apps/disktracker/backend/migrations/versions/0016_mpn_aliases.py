"""MPNs are stored uppercase without whitespace, and a drive can have alias MPNs
(vendor variants) that route prices to it."""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mpn_aliases",
        sa.Column("alias", sa.String(100), primary_key=True),
        sa.Column("drive_id", sa.Uuid(), sa.ForeignKey("drives.id"), nullable=False),
    )
    # Normalize existing MPNs unless that would collide with another drive; such pairs are
    # left for the user to join with an alias, which merges them.
    op.execute(
        """
        UPDATE drives d SET mpn = upper(regexp_replace(d.mpn, '\\s+', '', 'g'))
        WHERE NOT EXISTS (
            SELECT 1 FROM drives o
            WHERE o.id <> d.id AND upper(regexp_replace(o.mpn, '\\s+', '', 'g'))
                = upper(regexp_replace(d.mpn, '\\s+', '', 'g'))
        )
        """
    )
    op.execute(
        "UPDATE listings SET mpn = drives.mpn FROM drives WHERE drives.id = listings.drive_id"
    )


def downgrade() -> None:
    op.drop_table("mpn_aliases")
