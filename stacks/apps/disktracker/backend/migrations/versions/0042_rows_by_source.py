"""A source's runs and what reviewers decided about its listings name a source that exists, and
go with it when it is deleted (its offers and listings waiting for review already name one, and
keep it). Refuses to run, naming them, while any names a source there is not."""

import sqlalchemy as sa
from alembic import op

revision = "0042"
down_revision = "0041"
branch_labels = None
depends_on = None

REFERENCES = (("collector_runs", "source"), ("scraped_matches", "source"))


def upgrade() -> None:
    connection = op.get_bind()
    unknown = {
        table: [
            row[0]
            for row in connection.execute(
                sa.text(
                    f"SELECT DISTINCT {column} FROM {table}"
                    f" WHERE {column} NOT IN (SELECT key FROM sources) ORDER BY 1"
                )
            )
        ]
        for table, column in REFERENCES
    }
    if any(unknown.values()):
        named = "; ".join(f"{table}: {', '.join(keys)}" for table, keys in unknown.items() if keys)
        raise RuntimeError(f"Rows name sources there are not ({named}). Add or remove them first.")
    for table, column in REFERENCES:
        op.create_foreign_key(
            f"fk_{table}_{column}", table, "sources", [column], ["key"], ondelete="CASCADE"
        )


def downgrade() -> None:
    for table, column in reversed(REFERENCES):
        op.drop_constraint(f"fk_{table}_{column}", table, type_="foreignkey")
