"""Shipping may be unknown (a collector could not see it); totals still count it as zero."""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("observations", "shipping_cents", nullable=True)


def downgrade() -> None:
    op.execute("UPDATE observations SET shipping_cents = 0 WHERE shipping_cents IS NULL")
    op.alter_column("observations", "shipping_cents", nullable=False)
