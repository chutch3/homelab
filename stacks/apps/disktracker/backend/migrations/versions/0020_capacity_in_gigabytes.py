"""Store capacity as whole decimal gigabytes (1 TB = 1000 GB) instead of TB with two
decimals, so cards and small drives (128 GB, 32 GB) can be recorded exactly."""

import sqlalchemy as sa
from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None

TABLES = {"drives": False, "unmatched": True}


def upgrade() -> None:
    for table, nullable in TABLES.items():
        op.add_column(table, sa.Column("capacity_gb", sa.Integer(), nullable=True))
        op.execute(f"UPDATE {table} SET capacity_gb = round(capacity_tb * 1000)")
        op.alter_column(table, "capacity_gb", nullable=nullable)
        op.drop_column(table, "capacity_tb")


def downgrade() -> None:
    for table, nullable in TABLES.items():
        op.add_column(table, sa.Column("capacity_tb", sa.Numeric(8, 2), nullable=True))
        op.execute(f"UPDATE {table} SET capacity_tb = round(capacity_gb / 1000.0, 2)")
        op.alter_column(table, "capacity_tb", nullable=nullable)
        op.drop_column(table, "capacity_gb")
