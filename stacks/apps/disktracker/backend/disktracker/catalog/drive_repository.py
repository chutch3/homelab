"""Drives and the MPNs that identify them. Each method works on the session of the operation that
calls it and never commits: the operation decides what is kept together."""

from collections.abc import Callable, Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select, union, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import Drive, MpnAlias
from disktracker.catalog.rules import capacity_label, fill_unknown
from disktracker.catalog.schemas import Specifications
from disktracker.catalog.views import drive_view
from disktracker.database import columns
from disktracker.errors import CapacityConflict, CapacityRequired, DriveNotFound, MpnTaken
from disktracker.facts import escaped, every_offer_facts


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

    def hold(self, session: Session, mpns: Iterable[str | None]) -> None:
        """Hold every MPN an operation may touch, all at its start and in one order, before any
        drive, offer or review row: two operations then never each hold what the other waits
        for (the catalog-wide lock order)."""
        for mpn in sorted({mpn for mpn in mpns if mpn}):
            hold_mpn(session, mpn)

    def owner_of(self, session: Session, mpn: str) -> UUID | None:
        """The drive that goes by this MPN, as its own MPN or another of its MPNs; None for none."""
        return session.scalar(select(Drive.id).where(Drive.mpn == mpn)) or session.scalar(
            select(MpnAlias.drive_id).where(MpnAlias.alias == mpn)
        )

    def capacity_of(self, session: Session, mpn: str) -> int | None:
        """The capacity of the drive that goes by this MPN; None when none does."""
        owner = self.owner_of(session, mpn)
        return None if owner is None else session.get_one(Drive, owner).capacity_gb

    def register(self, session: Session, mpn: str, capacity_gb: int | None) -> UUID:
        """The drive that goes by this MPN, held against other changes until the operation ends,
        or a new one under it with this capacity: what collecting needs of a drive. A capacity
        given that is not the drive's is refused, and a new drive needs one, whatever was judged
        of it before (catalog.acceptance)."""
        hold_mpn(session, mpn)
        owner = self.owner_of(session, mpn)
        if owner is None:
            if capacity_gb is None:
                raise CapacityRequired()
            owner = self.create(
                session, mpn=mpn, capacity_gb=capacity_gb, brand=None,
                specifications=Specifications().model_dump(mode="json"),
            ).id  # fmt: skip
        drive = session.scalars(select(Drive).where(Drive.id == owner).with_for_update()).one()
        if capacity_gb is not None and capacity_gb != drive.capacity_gb:
            raise CapacityConflict(
                f"MPN {drive.mpn} is recorded as {capacity_label(drive.capacity_gb)}."
                " Edit the drive's specifications to change its capacity."
            )
        return drive.id

    def correct(
        self,
        session: Session,
        drive_id: UUID,
        values: dict[str, Any],
        specifications: dict[str, Any] | None,
    ) -> None:
        """Change what is given of a drive (one that exists), its specifications one by one, and
        leave the rest as it is."""
        if specifications is not None:
            known = session.scalars(select(Drive.specifications).where(Drive.id == drive_id)).one()
            values = values | {
                "specifications": Specifications.model_validate(known | specifications).model_dump(
                    mode="json"
                )
            }
        if values:
            session.execute(update(Drive).where(Drive.id == drive_id).values(**values))

    def describe(
        self,
        session: Session,
        drive_id: UUID,
        specifications: dict[str, Any] | None,
        brand: str | None,
    ) -> None:
        """Take what a page says of a drive where nobody has said it: specifications left
        unknown, and a brand when it has none. What was entered stands."""
        drive = session.get_one(Drive, drive_id)
        if specifications is not None:
            filled = fill_unknown(
                Specifications.model_validate(drive.specifications).model_dump(mode="json"),
                specifications,
            )
            session.execute(update(Drive).where(Drive.id == drive_id).values(specifications=filled))
        if brand is not None:
            session.execute(
                update(Drive).where(Drive.id == drive_id, Drive.brand.is_(None)).values(brand=brand)
            )

    def attach_alias(self, session: Session, drive_id: UUID, alias: str) -> None:
        """Another MPN the drive goes by, one no drive goes by yet: refused otherwise, and never a
        reason to merge drives."""
        hold_mpn(session, alias)
        owner = self.owner_of(session, alias)
        if owner is not None:
            owning = session.scalars(select(Drive.mpn).where(Drive.id == owner)).one()
            raise MpnTaken(f"{alias} already identifies drive {owning}.")
        session.add(MpnAlias(alias=alias, drive_id=drive_id))
        session.flush()

    def view(self, session: Session, drive_id: UUID) -> dict[str, Any]:
        """A drive as the API shows it, with every other MPN it goes by."""
        drive = session.get(Drive, drive_id)
        if drive is None:
            raise DriveNotFound()
        aliases = session.scalars(
            select(MpnAlias.alias).where(MpnAlias.drive_id == drive_id).order_by(MpnAlias.alias)
        )
        return drive_view(drive, list(aliases))

    def identifiers(self, session: Session, drive_id: UUID) -> set[str]:
        """Every MPN a drive goes by: its own, and the others."""
        mpn = session.scalar(select(Drive.mpn).where(Drive.id == drive_id))
        if mpn is None:
            raise DriveNotFound()
        aliases = session.scalars(select(MpnAlias.alias).where(MpnAlias.drive_id == drive_id))
        return {mpn, *aliases}

    def lock_drives(
        self, session: Session, drive_ids: Iterable[UUID]
    ) -> dict[UUID, dict[str, Any]]:
        """Drives held against other changes until the operation ends, taken in id order, as
        they are now."""
        drives = session.scalars(
            select(Drive).where(Drive.id.in_(list(drive_ids))).order_by(Drive.id).with_for_update()
        )
        return {drive.id: columns(drive) for drive in drives}

    def absorb(
        self, session: Session, source_id: UUID, target_id: UUID, values: dict[str, Any]
    ) -> None:
        """The target goes by every MPN the source went by, and is what the merge made it; the
        source, with no offer left, is gone."""
        source_mpn = session.scalars(select(Drive.mpn).where(Drive.id == source_id)).one()
        session.execute(
            update(MpnAlias).where(MpnAlias.drive_id == source_id).values(drive_id=target_id)
        )
        session.execute(delete(Drive).where(Drive.id == source_id))
        session.add(MpnAlias(alias=source_mpn, drive_id=target_id))
        session.execute(update(Drive).where(Drive.id == target_id).values(**values))
        session.flush()

    def named(
        self, session: Session, words: str, limit: int, offset: int
    ) -> tuple[list[UUID], int]:
        """The drives any name of which has these words, as typed: its MPN, another of its MPNs,
        or any name an offer of it goes by (catalog offers, held ones too); those the words are
        an MPN of first, then by MPN. A part of them, and how many there are."""
        pattern = f"%{escaped(words)}%"
        facts = every_offer_facts().subquery()
        found = union(
            select(Drive.id).where(Drive.mpn.ilike(pattern, escape="\\")),
            select(MpnAlias.drive_id).where(MpnAlias.alias.ilike(pattern, escape="\\")),
            select(facts.c.drive_id).where(facts.c.names.ilike(pattern, escape="\\")),
        ).subquery()
        exact = or_(
            func.upper(Drive.mpn) == words.upper(),
            Drive.id.in_(
                select(MpnAlias.drive_id).where(func.upper(MpnAlias.alias) == words.upper())
            ),
        )
        chosen = select(Drive.id).join(found, found.c.id == Drive.id)
        total = session.scalar(select(func.count()).select_from(chosen.subquery())) or 0
        ids = session.scalars(
            chosen.order_by(exact.desc(), Drive.mpn, Drive.id).limit(limit).offset(offset)
        )
        return list(ids), total

    def titles(self, session: Session, drive_ids: list[UUID]) -> dict[UUID, str]:
        """What each of these drives is called: the title of its cheapest offer in stock, else
        of its cheapest offer, else its MPN."""
        facts = every_offer_facts().subquery()
        first = func.row_number().over(
            partition_by=facts.c.drive_id,
            order_by=(facts.c.in_stock.desc(), facts.c.per_tb, facts.c.id),
        )
        ranked = (
            select(facts.c.drive_id, facts.c.title, first.label("rank"))
            .where(facts.c.drive_id.in_(drive_ids))
            .subquery()
        )
        offered = dict(
            session.execute(select(ranked.c.drive_id, ranked.c.title).where(ranked.c.rank == 1))
            .tuples()
            .all()
        )
        mpns = session.execute(select(Drive.id, Drive.mpn).where(Drive.id.in_(drive_ids)))
        return {drive_id: offered.get(drive_id, mpn) for drive_id, mpn in mpns.tuples()}
