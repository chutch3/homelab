"""Why a run did not complete, when known: as its collector said for a failed run, as disktracker
found it for an abandoned one. Runs ended before say nothing."""

import sqlalchemy as sa
from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("collector_runs", sa.Column("reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("collector_runs", "reason")
