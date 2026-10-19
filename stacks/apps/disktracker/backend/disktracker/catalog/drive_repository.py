"""Drives and the MPNs that identify them. Each method works on the session of the operation that
calls it and never commits: the operation decides what is kept together."""

from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import Drive, MpnAlias
from disktracker.errors import MpnTaken


def hold_mpn(session: Session, mpn: str) -> None:
    """Hold an MPN until the operation ends, against any other that would make a drive go by it:
    a drive's own MPN and the others it goes by are kept apart, so no index can."""
    session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"mpn:{mpn}", 0))))


class DriveRepository:
    def __init__(self, next_id: Callable[[], UUID]) -> None:
        self.next_id = next_id

    def create(
        self,
        session: Session,
        *,
        mpn: str,
        capacity_gb: int,
        brand: str | None,
        specifications: dict[str, Any],
    ) -> Drive:
        """A new drive under an MPN no drive goes by: refused, whichever way one already does,
        even one that took it a moment before."""
        hold_mpn(session, mpn)
        made = session.scalar(
            pg_insert(Drive)
            .values(
                id=self.next_id(),
                mpn=mpn,
                capacity_gb=capacity_gb,
                brand=brand,
                specifications=specifications,
            )
            .on_conflict_do_nothing(index_elements=[Drive.mpn])
            .returning(Drive.id)
        )
        # Looked for once it is written, so an alias taken meanwhile is seen.
        if made is None or session.scalar(select(MpnAlias.alias).where(MpnAlias.alias == mpn)):
            raise MpnTaken(f"{mpn} already identifies a drive.")
        return session.get_one(Drive, made)
