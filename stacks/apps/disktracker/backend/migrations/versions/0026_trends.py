"""Each trend once worked out, so it is read back instead of worked out again for every request:
one answer for each period, split and allowance for unchecked offers, with when it was worked out
and the prices it was worked out from."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0026"
down_revision = "0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trends",
        sa.Column("days", sa.Integer(), primary_key=True),
        sa.Column("by", sa.String(20), primary_key=True),
        sa.Column("recent_days", sa.Integer(), primary_key=True),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stamp", sa.Text(), nullable=False),
        sa.Column("body", JSONB, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("trends")
