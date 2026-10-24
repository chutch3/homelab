"""Drives and the MPNs that identify them."""

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, or_, select, union, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import Drive, MpnAlias
from disktracker.catalog.rules import capacity_label, fill_unknown
from disktracker.catalog.schemas import Specifications
from disktracker.catalog.views import drive_view
from disktracker.database import Repository, columns
from disktracker.errors import CapacityConflict, CapacityRequired, DriveNotFound, MpnTaken
from disktracker.facts import escaped, every_offer_facts


def hold_mpn(session: Session, mpn: str) -> None:
    """Hold an MPN until the operation ends, against any other that would make a drive go by it:
    a drive's own MPN and the others it goes by are kept apart, so no index can."""
    session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended(f"mpn:{mpn}", 0))))


class DriveRepository(Repository):
    def create(
        self,
        *,
        mpn: str,
        capacity_gb: int,
        brand: str | None,
        specifications: dict[str, Any],
    ) -> Drive:
        """A new drive under an MPN no drive goes by: refused, whichever way one already does,
        even one that took it a moment before."""
        hold_mpn(self.session, mpn)
        made = self.session.scalar(
            pg_insert(Drive)
            .values(
                mpn=mpn,
                capacity_gb=capacity_gb,
                brand=brand,
                specifications=specifications,
            )
            .on_conflict_do_nothing(index_elements=[Drive.mpn])
            .returning(Drive.id)
        )
        # Looked for once it is written, so an alias taken meanwhile is seen.
        if made is None or self.session.scalar(select(MpnAlias.alias).where(MpnAlias.alias == mpn)):
            raise MpnTaken(f"{mpn} already identifies a drive.")
        return self.session.get_one(Drive, made)

    def hold(self, mpns: Iterable[str | None]) -> None:
        """Hold every MPN an operation may touch, all at its start and in one order, before any
        drive, offer or review row: two operations then never each hold what the other waits
        for (the catalog-wide lock order)."""
        for mpn in sorted({mpn for mpn in mpns if mpn}):
            hold_mpn(self.session, mpn)

    def owner_of(self, mpn: str) -> UUID | None:
        """The drive that goes by this MPN, as its own MPN or another of its MPNs; None for none."""
        return self.session.scalar(select(Drive.id).where(Drive.mpn == mpn)) or self.session.scalar(
            select(MpnAlias.drive_id).where(MpnAlias.alias == mpn)
        )

    def owners(self, mpns: Iterable[str]) -> dict[str, UUID]:
        """The drive each of these MPNs goes by, as its own or another of its MPNs, read
        together whatever their number; those no drive goes by are left out."""
        wanted = list(mpns)
        own = self.session.execute(select(Drive.mpn, Drive.id).where(Drive.mpn.in_(wanted)))
        other = self.session.execute(
            select(MpnAlias.alias, MpnAlias.drive_id).where(MpnAlias.alias.in_(wanted))
        )
        return dict(other.tuples().all()) | dict(own.tuples().all())

    def capacity_of(self, mpn: str) -> int | None:
        """The capacity of the drive that goes by this MPN; None when none does."""
        owner = self.owner_of(mpn)
        return None if owner is None else self.session.get_one(Drive, owner).capacity_gb

    def register(self, mpn: str, capacity_gb: int | None) -> UUID:
        """The drive that goes by this MPN, held against other changes until the operation ends,
        or a new one under it with this capacity: what collecting needs of a drive. A capacity
        given that is not the drive's is refused, and a new drive needs one, whatever was judged
        of it before (catalog.verdict)."""
        hold_mpn(self.session, mpn)
        owner = self.owner_of(mpn)
        if owner is None:
            if capacity_gb is None:
                raise CapacityRequired()
            owner = self.create(
                mpn=mpn, capacity_gb=capacity_gb, brand=None,
                specifications=Specifications().model_dump(mode="json"),
            ).id  # fmt: skip
        drive = self.session.scalars(select(Drive).where(Drive.id == owner).with_for_update()).one()
        if capacity_gb is not None and capacity_gb != drive.capacity_gb:
            raise CapacityConflict(
                f"MPN {drive.mpn} is recorded as {capacity_label(drive.capacity_gb)}."
                " Edit the drive's specifications to change its capacity."
            )
        return drive.id

    def correct(
        self,
        drive_id: UUID,
        values: dict[str, Any],
        specifications: dict[str, Any] | None,
    ) -> None:
        """Change what is given of a drive (one that exists), its specifications one by one, and
        leave the rest as it is."""
        if specifications is not None:
            known = self.session.scalars(
                select(Drive.specifications).where(Drive.id == drive_id)
            ).one()
            values = values | {
                "specifications": Specifications.model_validate(known | specifications).model_dump(
                    mode="json"
                )
            }
        if values:
            self.session.execute(update(Drive).where(Drive.id == drive_id).values(**values))

    def describe(
        self,
        drive_id: UUID,
        specifications: dict[str, Any] | None,
        brand: str | None,
    ) -> None:
        """Take what a page says of a drive where nobody has said it: specifications left
        unknown, and a brand when it has none. What was entered stands."""
        drive = self.session.get_one(Drive, drive_id)
        if specifications is not None:
            filled = fill_unknown(
                Specifications.model_validate(drive.specifications).model_dump(mode="json"),
                specifications,
            )
            self.session.execute(
                update(Drive).where(Drive.id == drive_id).values(specifications=filled)
            )
        if brand is not None:
            self.session.execute(
                update(Drive).where(Drive.id == drive_id, Drive.brand.is_(None)).values(brand=brand)
            )

    def attach_alias(self, drive_id: UUID, alias: str) -> None:
        """Another MPN the drive goes by, one no drive goes by yet: refused otherwise, and never a
        reason to merge drives."""
        hold_mpn(self.session, alias)
        owner = self.owner_of(alias)
        if owner is not None:
            owning = self.session.scalars(select(Drive.mpn).where(Drive.id == owner)).one()
            raise MpnTaken(f"{alias} already identifies drive {owning}.")
        self.session.add(MpnAlias(alias=alias, drive_id=drive_id))
        self.session.flush()

    def view(self, drive_id: UUID) -> dict[str, Any]:
        """A drive as the API shows it, with every other MPN it goes by."""
        found = self.views([drive_id])
        if drive_id not in found:
            raise DriveNotFound()
        return found[drive_id]

    def views(self, drive_ids: Iterable[UUID]) -> dict[UUID, dict[str, Any]]:
        """These drives as the API shows them, by id, read together whatever their number;
        those that are not there are left out."""
        ids = list(drive_ids)
        aliases: dict[UUID, list[str]] = {drive_id: [] for drive_id in ids}
        for drive_id, alias in self.session.execute(
            select(MpnAlias.drive_id, MpnAlias.alias)
            .where(MpnAlias.drive_id.in_(ids))
            .order_by(MpnAlias.alias)
        ).tuples():
            aliases[drive_id].append(alias)
        drives = self.session.scalars(select(Drive).where(Drive.id.in_(ids)))
        return {drive.id: drive_view(drive, aliases[drive.id]) for drive in drives}

    def identifiers(self, drive_id: UUID) -> set[str]:
        """Every MPN a drive goes by: its own, and the others."""
        mpn = self.session.scalar(select(Drive.mpn).where(Drive.id == drive_id))
        if mpn is None:
            raise DriveNotFound()
        aliases = self.session.scalars(select(MpnAlias.alias).where(MpnAlias.drive_id == drive_id))
        return {mpn, *aliases}

    def lock_drives(self, drive_ids: Iterable[UUID]) -> dict[UUID, dict[str, Any]]:
        """Drives held against other changes until the operation ends, taken in id order, as
        they are now."""
        drives = self.session.scalars(
            select(Drive).where(Drive.id.in_(list(drive_ids))).order_by(Drive.id).with_for_update()
        )
        return {drive.id: columns(drive) for drive in drives}

    def absorb(self, source_id: UUID, target_id: UUID, values: dict[str, Any]) -> None:
        """The target goes by every MPN the source went by, and is what the merge made it; the
        source, with no offer left, is gone."""
        source_mpn = self.session.scalars(select(Drive.mpn).where(Drive.id == source_id)).one()
        self.session.execute(
            update(MpnAlias).where(MpnAlias.drive_id == source_id).values(drive_id=target_id)
        )
        self.session.execute(delete(Drive).where(Drive.id == source_id))
        self.session.add(MpnAlias(alias=source_mpn, drive_id=target_id))
        self.session.execute(update(Drive).where(Drive.id == target_id).values(**values))
        self.session.flush()

    def named(self, words: str, limit: int, offset: int) -> tuple[list[UUID], int]:
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
        total = self.session.scalar(select(func.count()).select_from(chosen.subquery())) or 0
        ids = self.session.scalars(
            chosen.order_by(exact.desc(), Drive.mpn, Drive.id).limit(limit).offset(offset)
        )
        return list(ids), total

    def titles(self, drive_ids: list[UUID]) -> dict[UUID, str]:
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
            self.session.execute(
                select(ranked.c.drive_id, ranked.c.title).where(ranked.c.rank == 1)
            )
            .tuples()
            .all()
        )
        mpns = self.session.execute(select(Drive.id, Drive.mpn).where(Drive.id.in_(drive_ids)))
        return {drive_id: offered.get(drive_id, mpn) for drive_id, mpn in mpns.tuples()}
