"""One revision of everything a trend reads, counted by the database itself so that no way of
changing it can forget to: a price, an offer, a drive, a drive's other MPNs, or a store's name
added, changed or removed. It replaces the stamp of the prices and the revision of their past,
which between them missed what narrows a trend to some drives: a brand, a specification, a title,
an MPN or a store's name.

The revision is counted once for each piece of work that changes any of it, as that work commits,
so its row is held only for the moment of committing; a trend read in the same snapshot as the
revision is what that revision stands for."""

import sqlalchemy as sa
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None

# What a trend reads, and when it changes.
READ = {
    "observations": "INSERT OR UPDATE OR DELETE",
    "listings": "INSERT OR UPDATE OR DELETE",
    "drives": "INSERT OR UPDATE OR DELETE",
    "mpn_aliases": "INSERT OR UPDATE OR DELETE",
    "sources": "INSERT OR UPDATE OF name OR DELETE",
}

OLD_TRIGGERS = {
    "observations_revised": "AFTER UPDATE OR DELETE ON observations",
    "listings_revised": "AFTER UPDATE OF drive_id, store, condition OR DELETE ON listings",
    "drives_revised": "AFTER UPDATE OF capacity_gb OR DELETE ON drives",
}


def upgrade() -> None:
    for name, when in OLD_TRIGGERS.items():
        op.execute(f"DROP TRIGGER {name} ON {when.rsplit(' ', 1)[1]}")
    op.execute("DROP FUNCTION revise_history()")
    op.drop_table("history_revision")

    op.create_table(
        "trend_revision",
        sa.Column("id", sa.Boolean(), primary_key=True),
        sa.Column("revision", sa.BigInteger(), nullable=False),
        # The piece of work that last counted it, so that it counts each once.
        sa.Column("counted_by", sa.BigInteger()),
        sa.CheckConstraint("id", name="trend_revision_one_row"),
    )
    op.execute("INSERT INTO trend_revision (id, revision) VALUES (true, 0)")
    op.execute(
        "CREATE FUNCTION revise_trends() RETURNS trigger AS $$ BEGIN"
        " UPDATE trend_revision SET revision = revision + 1, counted_by = txid_current()"
        " WHERE counted_by IS DISTINCT FROM txid_current(); RETURN NULL;"
        " END $$ LANGUAGE plpgsql"
    )
    for table, events in READ.items():
        op.execute(
            f"CREATE CONSTRAINT TRIGGER {table}_revise_trends AFTER {events} ON {table}"
            " DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION revise_trends()"
        )
        op.execute(
            f"CREATE TRIGGER {table}_truncated_revise_trends AFTER TRUNCATE ON {table}"
            " FOR EACH STATEMENT EXECUTE FUNCTION revise_trends()"
        )

    # Trends kept before stand for a stamp no longer kept, and are worked out again.
    op.execute("DELETE FROM trends")
    op.drop_column("trends", "stamp")
    op.alter_column("trends", "revision", nullable=False)


def downgrade() -> None:
    op.execute("DELETE FROM trends")
    op.alter_column("trends", "revision", nullable=True)
    op.add_column("trends", sa.Column("stamp", sa.Text(), nullable=False))
    for table in READ:
        op.execute(f"DROP TRIGGER {table}_truncated_revise_trends ON {table}")
        op.execute(f"DROP TRIGGER {table}_revise_trends ON {table}")
    op.execute("DROP FUNCTION revise_trends()")
    op.drop_table("trend_revision")

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
    for name, when in OLD_TRIGGERS.items():
        op.execute(
            f"CREATE TRIGGER {name} {when} FOR EACH STATEMENT EXECUTE FUNCTION revise_history()"
        )
