"""Specifications keep only their plain values; verification status, sources,
Other descriptions and SMR management are dropped."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

INTERFACES = {"sata", "sas", "nvme_pcie", "usb"}
RECORDINGS = {"cmr", "smr"}
USES = {"nas", "surveillance", "enterprise", "desktop", "archive"}

drives = sa.table("drives", sa.column("id", sa.Uuid()), sa.column("specifications", JSONB()))


def plain(evidence: dict) -> dict:
    def value(key: str) -> object:
        entry = evidence.get(key) or {}
        return entry.get("value") if isinstance(entry, dict) else entry

    interface, recording, uses = value("interface"), value("recording_type"), value("intended_use")
    return {
        "interface": interface if interface in INTERFACES else "unknown",
        "recording_type": recording if recording in RECORDINGS else "unknown",
        "intended_use": [use for use in (uses if isinstance(uses, list) else []) if use in USES],
    }


def upgrade() -> None:
    connection = op.get_bind()
    for drive_id, specifications in connection.execute(
        sa.select(drives.c.id, drives.c.specifications)
    ).all():
        connection.execute(
            sa.update(drives)
            .where(drives.c.id == drive_id)
            .values(specifications=plain(specifications or {}))
        )


def downgrade() -> None:
    connection = op.get_bind()
    for drive_id, specifications in connection.execute(
        sa.select(drives.c.id, drives.c.specifications)
    ).all():
        evidence = {
            "interface": {"value": specifications.get("interface", "unknown")},
            "recording_type": {"value": specifications.get("recording_type", "unknown")},
            "intended_use": {"value": specifications.get("intended_use") or ["unknown"]},
        }
        connection.execute(
            sa.update(drives).where(drives.c.id == drive_id).values(specifications=evidence)
        )
