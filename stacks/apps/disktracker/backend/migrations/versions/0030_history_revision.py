"""A revision of the past that trends read, counted by the database itself so that no way of
changing it can forget to: a price changed or removed, an offer moved to another drive, store or
condition or removed, a drive's capacity changed or the drive removed. A kept trend worked out at
another revision is worked out again, all of it. Recording a price or a check leaves the past as
it was, and only moves today's point."""

import sqlalchemy as sa
from alembic import op

revision = "0030"
down_revision = "0029"
branch_labels = None
depends_on = None

TRIGGERS = {
    "observations_revised": "AFTER UPDATE OR DELETE ON observations",
    "listings_revised": "AFTER UPDATE OF drive_id, store, condition OR DELETE ON listings",
    "drives_revised": "AFTER UPDATE OF capacity_gb OR DELETE ON drives",
}


def upgrade() -> None:
    op.create_table(
        "history_revision",
        sa.Column("id", sa.Boolean(), primary_key=True),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("id", name="history_revision_one_row"),
    )
    op.execute("INSERT INTO history_revision (id, revision) VALUES (true, 0)")
    op.execute(
        "CREATE FUNCTION revise_history() RETURNS trigger AS $$ BEGIN"
        " UPDATE history_revision SET revision = revision + 1; RETURN NULL;"
        " END $$ LANGUAGE plpgsql"
    )
    for name, when in TRIGGERS.items():
        op.execute(
            f"CREATE TRIGGER {name} {when} FOR EACH STATEMENT EXECUTE FUNCTION revise_history()"
        )
    # Trends kept before have no revision, and are worked out again.
    op.add_column("trends", sa.Column("revision", sa.BigInteger()))


def downgrade() -> None:
    op.drop_column("trends", "revision")
    for name, when in TRIGGERS.items():
        table = when.rsplit(" ", 1)[1]
        op.execute(f"DROP TRIGGER {name} ON {table}")
    op.execute("DROP FUNCTION revise_history()")
    op.drop_table("history_revision")
