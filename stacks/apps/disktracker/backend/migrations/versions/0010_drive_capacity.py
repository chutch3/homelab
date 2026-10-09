"""Capacity is a property of the drive (its MPN), not of each offer, so every
offer for an MPN shares one capacity and one $/TB basis."""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("drives", sa.Column("capacity_tb", sa.Numeric(8, 2)))
    # Offers could disagree before; the drive takes the capacity most of its offers used.
    op.execute(
        """
        UPDATE drives SET capacity_tb = (
            SELECT capacity_tb FROM listings WHERE listings.drive_id = drives.id
            GROUP BY capacity_tb ORDER BY count(*) DESC, capacity_tb LIMIT 1
        )
        """
    )
    op.execute("DELETE FROM drives WHERE capacity_tb IS NULL")
    op.alter_column("drives", "capacity_tb", nullable=False)
    op.alter_column("listings", "drive_id", nullable=False)
    op.drop_column("listings", "capacity_tb")


def downgrade() -> None:
    op.add_column("listings", sa.Column("capacity_tb", sa.Numeric(8, 2)))
    op.execute(
        "UPDATE listings SET capacity_tb = drives.capacity_tb FROM drives"
        " WHERE drives.id = listings.drive_id"
    )
    op.alter_column("listings", "capacity_tb", nullable=False)
    op.alter_column("listings", "drive_id", nullable=True)
    op.drop_column("drives", "capacity_tb")
