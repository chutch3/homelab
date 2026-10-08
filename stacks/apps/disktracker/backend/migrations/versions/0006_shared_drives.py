"""Shared Drive records keyed by MPN, so specifications live once per drive
instead of being re-entered and separately verified on every listing."""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "drives",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("mpn", sa.String(100), nullable=False, unique=True),
        sa.Column("specifications", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column("listings", sa.Column("drive_id", sa.Uuid(), sa.ForeignKey("drives.id")))
    op.add_column("corrections", sa.Column("drive_id", sa.Uuid(), sa.ForeignKey("drives.id")))
    op.alter_column("corrections", "listing_id", nullable=True)

    connection = op.get_bind()
    listings = sa.table(
        "listings",
        sa.column("id", sa.Uuid()),
        sa.column("mpn", sa.String()),
        sa.column("specifications", JSONB()),
        sa.column("drive_id", sa.Uuid()),
    )
    drives = sa.table(
        "drives",
        sa.column("id", sa.Uuid()),
        sa.column("mpn", sa.String()),
        sa.column("specifications", JSONB()),
    )
    rows = connection.execute(
        sa.select(listings.c.id, listings.c.mpn, listings.c.specifications).where(
            listings.c.mpn.is_not(None)
        )
    ).all()
    drive_id_by_mpn: dict[str, uuid.UUID] = {}
    for listing_id, mpn, specifications in rows:
        if mpn not in drive_id_by_mpn:
            drive_id = uuid.uuid4()
            drive_id_by_mpn[mpn] = drive_id
            connection.execute(
                sa.insert(drives).values(id=drive_id, mpn=mpn, specifications=specifications)
            )
        connection.execute(
            sa.update(listings)
            .where(listings.c.id == listing_id)
            .values(drive_id=drive_id_by_mpn[mpn])
        )

    op.drop_column("listings", "specifications")


def downgrade() -> None:
    op.add_column(
        "listings",
        sa.Column("specifications", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )
    connection = op.get_bind()
    listings = sa.table(
        "listings",
        sa.column("id", sa.Uuid()),
        sa.column("drive_id", sa.Uuid()),
        sa.column("specifications", JSONB()),
    )
    drives = sa.table("drives", sa.column("id", sa.Uuid()), sa.column("specifications", JSONB()))
    for drive_id, specifications in connection.execute(
        sa.select(drives.c.id, drives.c.specifications)
    ).all():
        connection.execute(
            sa.update(listings)
            .where(listings.c.drive_id == drive_id)
            .values(specifications=specifications)
        )
    op.drop_column("listings", "drive_id")
    op.alter_column("corrections", "listing_id", nullable=False)
    op.drop_column("corrections", "drive_id")
    op.drop_table("drives")
