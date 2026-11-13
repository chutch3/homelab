"""Why an offer is held out of every ranking, distribution and trend while a person settles what
its store page is: the doubt its page was last collected with. Offers recorded before they would
have been doubted are held by scripts/hold-doubted-offers.py, run once by hand; this changes no
offer."""

import sqlalchemy as sa
from alembic import op

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("listings", sa.Column("held_reason", sa.String(40)))


def downgrade() -> None:
    op.drop_column("listings", "held_reason")
