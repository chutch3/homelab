"""A listing that names an MPN another drive already goes by waits for review whole: kept with
that MPN and the drive it was found to be, as evidence for the reviewer. No drive is merged."""

import sqlalchemy as sa
from alembic import op

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("unmatched", sa.Column("conflict_mpn", sa.String(100)))
    op.add_column(
        "unmatched",
        sa.Column(
            "conflict_drive_id",
            sa.Uuid(),
            sa.ForeignKey("drives.id", name="fk_unmatched_conflict_drive", ondelete="SET NULL"),
        ),
    )


def downgrade() -> None:
    op.execute("DELETE FROM unmatched WHERE reason = 'alias_conflict'")
    op.drop_column("unmatched", "conflict_drive_id")
    op.drop_column("unmatched", "conflict_mpn")
