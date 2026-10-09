"""Each collector run's outcome, as the collector reports it, for the admin overview."""

import sqlalchemy as sa
from alembic import op

revision = "0022"
down_revision = "0021"
branch_labels = None
depends_on = None

COUNTS = ("seen", "recorded", "queued", "ignored", "failed", "rechecked", "recheck_failed")


def upgrade() -> None:
    op.create_table(
        "collector_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        *(sa.Column(count, sa.Integer(), nullable=False) for count in COUNTS),
    )
    op.create_index(
        "ix_collector_runs_source_finished", "collector_runs", ["source", "finished_at"]
    )


def downgrade() -> None:
    op.drop_table("collector_runs")
