"""Runs with a lifecycle: registered as they start under an id the collector chooses, updated
as they go, and ended with a status (completed, failed, stopped, or abandoned when the collector
no longer has them). What a run in progress has done lives on the run itself, so the table of
runs in progress goes. Runs reported before have ended: completed, stopped or failed as they
said."""

import sqlalchemy as sa
from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

COUNTS = ("seen", "recorded", "queued", "ignored", "failed")


def upgrade() -> None:
    op.add_column("collector_runs", sa.Column("status", sa.String(20)))
    op.add_column("collector_runs", sa.Column("updated_at", sa.DateTime(timezone=True)))
    op.execute(
        "UPDATE collector_runs SET updated_at = finished_at, status = CASE"
        " WHEN completed THEN 'completed' WHEN stopped THEN 'stopped' ELSE 'failed' END"
    )
    op.alter_column("collector_runs", "status", nullable=False)
    op.alter_column("collector_runs", "updated_at", nullable=False)
    op.alter_column("collector_runs", "finished_at", nullable=True)
    op.drop_column("collector_runs", "completed")
    op.drop_column("collector_runs", "stopped")
    op.create_index("ix_collector_runs_source_started", "collector_runs", ["source", "started_at"])
    op.drop_table("collector_activity")


def downgrade() -> None:
    op.create_table(
        "collector_activity",
        sa.Column("source", sa.String(40), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        *(sa.Column(count, sa.Integer(), nullable=False) for count in COUNTS),
    )
    op.drop_index("ix_collector_runs_source_started", "collector_runs")
    op.add_column("collector_runs", sa.Column("completed", sa.Boolean()))
    op.add_column(
        "collector_runs",
        sa.Column("stopped", sa.Boolean(), nullable=False, server_default="false"),
    )
    # A run still going, or abandoned, is reported as one that did not complete.
    op.execute(
        "UPDATE collector_runs SET completed = (status = 'completed'),"
        " stopped = (status = 'stopped'), finished_at = COALESCE(finished_at, updated_at)"
    )
    op.alter_column("collector_runs", "completed", nullable=False)
    op.alter_column("collector_runs", "finished_at", nullable=False)
    op.drop_column("collector_runs", "updated_at")
    op.drop_column("collector_runs", "status")
