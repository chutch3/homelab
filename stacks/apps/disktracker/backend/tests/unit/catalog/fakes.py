"""The catalog services' own collaborators, stood in for: a session factory whose sessions say
whether they were committed, and repositories that answer as a test sets them and keep, in
order, what each was asked. What the repositories do to a database is the PostgreSQL tests'
(tests/integration)."""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

from disktracker.errors import DriveNotFound, OfferNotFound

# What the fakes answer with for what they make: a drive, an offer, a price, a review item.
MADE_DRIVE, MADE_OFFER, MADE_PRICE, QUEUED_ITEM = (UUID(int=n) for n in (900, 800, 700, 600))


class FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


class FakeSessions:
    """Opens a session for each operation, and keeps them."""

    def __init__(self) -> None:
        self.opened: list[FakeSession] = []

    @contextmanager
    def __call__(self) -> Iterator[FakeSession]:
        session = FakeSession()
        self.opened.append(session)
        yield session

    @property
    def committed(self) -> bool:
        return any(session.committed for session in self.opened)


class Asked:
    """Keeps every call, by name, with what it was asked (the session left out)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, Any]] = []

    def asked(self, name: str, *args: Any, **kwargs: Any) -> None:
        """Keyword arguments as (args, kwargs); one argument alone as itself."""
        self.calls.append((name, (args, kwargs) if kwargs else args[0] if len(args) == 1 else args))

    def names(self) -> list[str]:
        return [name for name, _ in self.calls]

    def of(self, name: str) -> list[Any]:
        return [asked for called, asked in self.calls if called == name]


class FakeDrives(Asked):
    """Drives by id (their columns), the MPNs each goes by, and the drive each MPN names."""

    def __init__(
        self,
        drives: dict[UUID, dict[str, Any]] | None = None,
        owners: dict[str, UUID] | None = None,
        identifiers: dict[UUID, list[set[str]]] | None = None,
        made: UUID = MADE_DRIVE,
    ) -> None:
        super().__init__()
        self.drives = drives or {}
        self.owned = owners or {}
        # What each drive goes by, as each read of it finds it: the last read stands.
        self.goes_by = identifiers or {}
        self.made = made

    def hold(self, session: Any, mpns: Any) -> None:
        self.asked("hold", sorted({mpn for mpn in mpns if mpn}))

    def lock_drives(self, session: Any, drive_ids: Any) -> dict[UUID, dict[str, Any]]:
        ids = list(drive_ids)
        self.asked("lock_drives", ids)
        return {drive_id: self.drives[drive_id] for drive_id in ids if drive_id in self.drives}

    def owner_of(self, session: Any, mpn: str) -> UUID | None:
        return self.owned.get(mpn)

    def owners(self, session: Any, mpns: Any) -> dict[str, UUID]:
        return {mpn: self.owned[mpn] for mpn in mpns if mpn in self.owned}

    def capacity_of(self, session: Any, mpn: str) -> int | None:
        owner = self.owned.get(mpn)
        return None if owner is None else int(self.drives[owner]["capacity_gb"])

    def identifiers(self, session: Any, drive_id: UUID) -> set[str]:
        if drive_id not in self.goes_by:
            raise DriveNotFound()
        reads = self.goes_by[drive_id]
        return reads.pop(0) if len(reads) > 1 else reads[0]

    def register(self, session: Any, mpn: str, capacity_gb: int | None) -> UUID:
        self.asked("register", mpn, capacity_gb)
        return self.owned.get(mpn, self.made)

    def describe(self, session: Any, drive_id: UUID, specifications: Any, brand: Any) -> None:
        self.asked("describe", drive_id, specifications, brand)

    def attach_alias(self, session: Any, drive_id: UUID, alias: str) -> None:
        self.asked("attach_alias", drive_id, alias)

    def correct(self, session: Any, drive_id: UUID, values: Any, specifications: Any) -> None:
        self.asked("correct", drive_id, values, specifications)

    def absorb(self, session: Any, source: UUID, target: UUID, values: Any) -> None:
        self.asked("absorb", source, target, values)

    def named(self, session: Any, words: str, limit: int, offset: int) -> tuple[list[UUID], int]:
        self.asked("named", words, limit, offset)
        found = [drive_id for drive_id in self.drives if words in self.drives[drive_id]["mpn"]]
        return found[offset:][:limit], len(found)

    def view(self, session: Any, drive_id: UUID) -> dict[str, Any]:
        if drive_id not in self.drives:
            raise DriveNotFound()
        return {"id": drive_id, "mpn": self.drives[drive_id]["mpn"]}

    def views(self, session: Any, drive_ids: Any) -> dict[UUID, dict[str, Any]]:
        return {drive_id: self.view(session, drive_id) for drive_id in drive_ids}

    def titles(self, session: Any, drive_ids: Any) -> dict[UUID, str]:
        return {drive_id: f"Title of {self.drives[drive_id]['mpn']}" for drive_id in drive_ids}


class FakeOffers(Asked):
    """Offers by id, and a save key's earlier answer, if it had one."""

    def __init__(
        self,
        offers: set[UUID] | None = None,
        replay: dict[str, Any] | None = None,
        made: UUID = MADE_OFFER,
        price: UUID | None = MADE_PRICE,
        priced: bool = False,
        combined: list[tuple[UUID, UUID]] | None = None,
        prices: dict[UUID, tuple[UUID, bool]] | None = None,
    ) -> None:
        super().__init__()
        self.offers = offers or set()
        self.replay, self.made, self.price = replay, made, price
        self.has_price = priced
        self.combined = combined or []
        # Each price kept: its offer, and whether the offer has another.
        self.kept = prices or {}

    def claim(self, session: Any, key: UUID, fingerprint: str) -> dict[str, Any] | None:
        self.asked("claim", key)
        return self.replay

    def answer(self, session: Any, key: UUID, result: dict[str, Any]) -> None:
        self.asked("answer", key, result)

    def lock(self, session: Any, offer_id: UUID) -> None:
        self.asked("lock", offer_id)
        if offer_id not in self.offers:
            raise OfferNotFound()

    def offer_for(self, session: Any, **identity: Any) -> UUID:
        self.asked("offer_for", **identity)
        return self.made

    def record(self, session: Any, offer_id: UUID, price: Any, provenance: str) -> UUID | None:
        self.asked("record", offer_id, price, provenance)
        return self.price

    def priced(self, session: Any, **identity: Any) -> bool:
        return self.has_price

    def hold(self, session: Any, **identity: Any) -> None:
        self.asked("hold", **identity)

    def release(self, session: Any, offer_id: UUID) -> None:
        self.asked("release", offer_id)

    def consolidate(self, session: Any, source: UUID, target: UUID) -> list[tuple[UUID, UUID]]:
        self.asked("consolidate", source, target)
        return self.combined

    def edit(self, session: Any, offer_id: UUID, fields: dict[str, Any]) -> None:
        self.asked("edit", offer_id, fields)

    def with_history(self, session: Any, offer_id: UUID) -> dict[str, Any]:
        return {"id": str(offer_id)}

    def delete(self, session: Any, offer_id: UUID) -> None:
        self.asked("delete", offer_id)

    def offer_priced(self, session: Any, price_id: UUID) -> UUID | None:
        return self.kept[price_id][0] if price_id in self.kept else None

    def remove_price(self, session: Any, offer_id: UUID, price_id: UUID) -> bool:
        self.asked("remove_price", offer_id, price_id)
        return self.kept[price_id][1]


class FakeReviews(Asked):
    """Items waiting for review by id, a listing's remembered decision, and a decision's
    earlier answer, if it had one."""

    def __init__(
        self,
        items: dict[UUID, dict[str, Any]] | None = None,
        decided: dict[str, Any] | None = None,
        replay: dict[str, Any] | None = None,
        queued: UUID = QUEUED_ITEM,
    ) -> None:
        super().__init__()
        self.items = items or {}
        self.decided, self.replay, self.queued = decided, replay, queued
        # The queue as it is read: items as kept.
        self.queue_read: list[Any] = []

    def waiting(self, session: Any, *asked: Any) -> tuple[list[Any], int]:
        return list(self.queue_read), len(self.queue_read)

    def claim_decision(self, session: Any, item_id: UUID, decision: Any) -> dict[str, Any] | None:
        self.asked("claim_decision", item_id)
        return self.replay

    def answer_decision(self, session: Any, item_id: UUID, result: Any) -> None:
        self.asked("answer_decision", item_id, result)

    def peek(self, session: Any, item_id: UUID) -> dict[str, Any]:
        return self.items[item_id]

    def take(self, session: Any, item_id: UUID) -> dict[str, Any]:
        self.asked("take", item_id)
        return self.items.pop(item_id)

    def remember(self, session: Any, listing: Any, **decision: Any) -> None:
        self.asked("remember", tuple(listing), **decision)

    def decision_for(self, session: Any, listing: Any) -> dict[str, Any] | None:
        return self.decided

    def queue(self, session: Any, listing: Any, fields: Any, seen_at: Any) -> UUID:
        self.asked("queue", tuple(listing), fields)
        return self.queued

    def clear(self, session: Any, listing: Any) -> None:
        self.asked("clear", tuple(listing))

    def repoint(self, session: Any, source: UUID, target: UUID) -> None:
        self.asked("repoint", source, target)
