"""Prices are append-only and mistakes are deleted, so correction history,
edit revisions and archives are no longer kept."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("corrections")
    op.drop_constraint("listings_not_own_duplicate", "listings", type_="check")
    op.drop_constraint("listings_duplicate_fk", "listings", type_="foreignkey")
    op.drop_column("listings", "duplicate_of")
    op.drop_column("listings", "archived_at")
    op.drop_column("listings", "revision")
    op.drop_column("drives", "revision")


def downgrade() -> None:
    op.add_column("drives", sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column(
        "listings", sa.Column("revision", sa.Integer(), nullable=False, server_default="1")
    )
    op.add_column("listings", sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.add_column("listings", sa.Column("duplicate_of", sa.Uuid()))
    op.create_foreign_key("listings_duplicate_fk", "listings", "listings", ["duplicate_of"], ["id"])
    op.create_check_constraint("listings_not_own_duplicate", "listings", "duplicate_of <> id")
    op.create_table(
        "corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("listing_id", sa.Uuid(), sa.ForeignKey("listings.id")),
        sa.Column("drive_id", sa.Uuid(), sa.ForeignKey("drives.id")),
        sa.Column("observation_id", sa.Uuid(), sa.ForeignKey("observations.id")),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("before", JSONB(), nullable=False),
        sa.Column("after", JSONB(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("corrected_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("listing_id", "revision", name="corrections_listing_revision"),
    )
