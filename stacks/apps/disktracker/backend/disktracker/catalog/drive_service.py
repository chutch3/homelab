"""Drives as people find, make, correct and join them: a drive read, or found by an MPN it goes by
or words any name of it has; one made on its own before any price of it, what is given of one
corrected, another MPN it goes by, and one merged into another, the only way two drives become
one. Each is one piece of work; a merge, with its save key, is answered again as it
was when sent again."""

from hashlib import sha256
from typing import Any
from uuid import UUID

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.review_repository import ReviewRepository
from disktracker.catalog.rules import merged_drive
from disktracker.catalog.schemas import DriveEdit, DriveInput, DriveLookup, MergeInput
from disktracker.catalog.views import drive_view
from disktracker.database import Transactions, transactional
from disktracker.errors import DriveNotFound, MergeConflict, SameDrive


class DriveService:
    def __init__(
        self,
        transactions: Transactions,
        drives: DriveRepository,
        offers: OfferRepository,
        reviews: ReviewRepository,
    ) -> None:
        self.transactions = transactions
        self.drives, self.offers, self.reviews = drives, offers, reviews

    @transactional(read_only=True)
    def get(self, drive_id: UUID) -> dict[str, Any]:
        return self.drives.view(drive_id)

    @transactional(read_only=True)
    def find(self, lookup: DriveLookup) -> dict[str, Any]:
        """The drive that goes by an MPN, or those words name, a part at a time, each named."""
        if lookup.mpn is not None:
            owner = self.drives.owner_of(lookup.mpn)
            found = [] if owner is None else [owner]
            ids, total = found[lookup.offset :][: lookup.limit], len(found)
        else:
            ids, total = self.drives.named(lookup.q, lookup.limit, lookup.offset)
        titles, views = self.drives.titles(ids), self.drives.views(ids)
        items = [{"drive": views[drive_id], "title": titles[drive_id]} for drive_id in ids]
        return {"items": items, "total": total, "limit": lookup.limit, "offset": lookup.offset}

    @transactional
    def create(self, entry: DriveInput) -> dict[str, Any]:
        """A drive made on its own, before any price of it."""
        drive = self.drives.create(
            mpn=entry.mpn,
            capacity_gb=entry.capacity_gb,
            brand=entry.brand,
            specifications=entry.specifications.model_dump(mode="json"),
        )
        return drive_view(drive, [])

    @transactional
    def edit(self, drive_id: UUID, entry: DriveEdit) -> dict[str, Any]:
        """Correct what is given of a drive, down to each specification, and leave the rest as
        it is. It touches no MPN, so only the drive is held."""
        given = entry.model_dump(mode="json", exclude_unset=True)
        values = {key: given[key] for key in ("capacity_gb", "brand") if key in given}
        if not self.drives.lock_drives([drive_id]):
            raise DriveNotFound()
        self.drives.correct(drive_id, values, given.get("specifications"))
        return self.drives.view(drive_id)

    @transactional
    def add_alias(self, drive_id: UUID, alias: str) -> dict[str, Any]:
        """Another MPN the drive goes by: one no drive goes by yet. One any drive goes by is
        refused, naming that drive, and nothing changes; joining two drives is a merge."""
        self.drives.hold([alias])
        if not self.drives.lock_drives([drive_id]):
            raise DriveNotFound()
        self.drives.attach_alias(drive_id, alias)
        return self.drives.view(drive_id)

    @transactional
    def merge(self, source_id: UUID, entry: MergeInput, request_id: UUID) -> dict[str, Any]:
        """Merge the source drive into the target, which survives: with every MPN the source
        went by, its brand where the target has none and its specifications where the target's
        are unknown, and its offers (combined with the target's of the same store, seller and
        condition). Drives that both know a capacity or specification and differ on it are not
        merged. Locks are taken in the catalog-wide order: the save key, every MPN both drives
        go by, the two drives, their offers, then what waits for review."""
        target_id = entry.target_drive_id
        if source_id == target_id:
            raise SameDrive()
        sent = sha256(f"merge:{source_id}:{entry.model_dump_json()}".encode()).hexdigest()
        replay = self.offers.claim(request_id, sent)
        if replay is not None:
            return replay
        read = {d: self.drives.identifiers(d) for d in (source_id, target_id)}
        self.drives.hold(set().union(*read.values()))
        held = {d: self.drives.identifiers(d) for d in (source_id, target_id)}
        if held != read:
            raise MergeConflict([], "What the drives go by changed as they were merged: try again.")
        drives = self.drives.lock_drives((source_id, target_id))
        values = merged_drive(drives[target_id], drives[source_id])
        combined = self.offers.consolidate(source_id, target_id)
        self.reviews.repoint(source_id, target_id)
        self.drives.absorb(source_id, target_id, values)
        result = {
            "status": "merged",
            "drive_id": str(target_id),
            "absorbed_drive_id": str(source_id),
            "combined_offers": [
                {"absorbed_offer_id": str(absorbed), "offer_id": str(survivor)}
                for absorbed, survivor in combined
            ],
        }
        self.offers.answer(request_id, result)
        return result
