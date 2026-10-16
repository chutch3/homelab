"""Each review decision, kept after its item leaves the queue: the same decision sent again is
answered as it was the first time, and a different one is refused."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0029"
down_revision = "0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "review_decisions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("decision", JSONB(), nullable=False),
        sa.Column("result", JSONB()),
    )


def downgrade() -> None:
    op.drop_table("review_decisions")
