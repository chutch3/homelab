"""What the collector is doing now, as it says while it runs, so the admin page can show a run
in progress and ask it to stop: each run's progress, when a collector was last heard from, when
a source's run was asked to stop, and whether a run ended because it was."""

import sqlalchemy as sa
from alembic import op

revision = "0025"
down_revision = "0024"
branch_labels = None
depends_on = None

COUNTS = ("seen", "recorded", "queued", "ignored", "failed")


def upgrade() -> None:
    op.create_table(
        "collector_activity",
        sa.Column("source", sa.String(40), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *(sa.Column(count, sa.Integer(), nullable=False) for count in COUNTS),
    )
    op.create_table(
        "collector_contact",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("sources", sa.Column("stop_requested_at", sa.DateTime(timezone=True)))
    op.add_column(
        "collector_runs",
        sa.Column("stopped", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("collector_runs", "stopped")
    op.drop_column("sources", "stop_requested_at")
    op.drop_table("collector_contact")
    op.drop_table("collector_activity")
