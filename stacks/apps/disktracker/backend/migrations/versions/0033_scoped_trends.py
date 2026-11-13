"""Trends kept for the drives a page narrows to, each apart from those of every drive. Trends
kept before are forgotten: they are worked out again when next asked for, saying now when the
first price was seen."""

import sqlalchemy as sa
from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM trends")
    op.add_column("trends", sa.Column("scope", sa.Text(), nullable=False, server_default=""))
    op.drop_constraint("trends_pkey", "trends", type_="primary")
    op.create_primary_key("trends_pkey", "trends", ["days", "by", "recent_days", "scope"])


def downgrade() -> None:
    op.execute("DELETE FROM trends WHERE scope <> ''")
    op.drop_constraint("trends_pkey", "trends", type_="primary")
    op.create_primary_key("trends_pkey", "trends", ["days", "by", "recent_days"])
    op.drop_column("trends", "scope")
