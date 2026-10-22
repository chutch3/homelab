"""Listings waiting for review, and what reviewers decided listings are. Each method works on the
session of the operation that calls it and never commits: the operation decides what is kept
together."""

from collections.abc import Callable
from datetime import datetime
from typing import Any, NamedTuple, Self
from uuid import UUID

from sqlalchemy import delete, func, literal_column, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import Drive, ReviewDecision, ReviewItem, ScrapedMatch
from disktracker.catalog.rules import decided_again
from disktracker.database import by_column, columns
from disktracker.errors import ReviewItemNotFound


class Listing(NamedTuple):
    """What one store page says one offer is, before anyone trusts it: its store, page, seller,
    and the MPN and condition the page gave, "" where it gave none. Two products of a page that
    say all of this alike are one listing (a known limit)."""

    store: str
    url: str
    seller: str
    mpn: str
    condition: str

    @classmethod
    def of(cls, store: str, url: str, seller: str, mpn: str | None, condition: str | None) -> Self:
        return cls(store, url, seller, mpn or "", condition or "")


def _blank(column: Any) -> Any:
    # As the unique index on unmatched writes it, so that a conflict finds that index.
    return func.coalesce(column, literal_column("''"))


def listing_of(item: dict[str, Any]) -> Listing:
    """The listing a queued item is of, as its page gave it."""
    return Listing.of(item["store"], item["url"], item["seller"], item["mpn"], item["condition"])


class ReviewRepository:
    def __init__(self, next_id: Callable[[], UUID]) -> None:
        self.next_id = next_id

    def waiting(
        self,
        session: Session,
        store: str | None,
        reason: str | None,
        limit: int | None,
        offset: int,
    ) -> tuple[list[ReviewItem], int]:
        """The offers waiting for review, newest first: those seen at this store and waiting for
        this reason when given, limit of them from offset; and how many there are in all,
        whatever the limit."""
        wanted = [
            column == value
            for column, value in ((ReviewItem.store, store), (ReviewItem.reason, reason))
            if value is not None
        ]
        total = session.scalar(select(func.count()).select_from(ReviewItem).where(*wanted))
        items = session.scalars(
            select(ReviewItem)
            .where(*wanted)
            .order_by(ReviewItem.last_seen_at.desc(), ReviewItem.id)
            .limit(limit)
            .offset(offset)
        )
        return list(items), total or 0

    def decision_for(self, session: Session, listing: Listing) -> dict[str, Any] | None:
        """What a reviewer decided this listing is, if one has; no other listing's decision,
        though it shares the page."""
        decided = session.get(ScrapedMatch, tuple(listing))
        if decided is None:
            return None
        # With the MPN its drive goes by now, which is what identifies what is collected.
        mpn = session.scalar(select(Drive.mpn).where(Drive.id == decided.drive_id))
        return columns(decided) | {"mpn": mpn}

    def queue(
        self, session: Session, listing: Listing, fields: dict[str, Any], seen_at: datetime
    ) -> UUID:
        """Keep a listing waiting for review, in place of what was kept of the same listing
        before, and of no other: the item's id."""
        table = ReviewItem.__table__
        item_id: UUID = session.scalars(
            pg_insert(table)
            .values(
                by_column(
                    ReviewItem,
                    {"id": self.next_id(), "first_seen_at": seen_at, "last_seen_at": seen_at, **fields},
                )
            )
            .on_conflict_do_update(
                index_elements=[
                    table.c.source, table.c.url, table.c.seller,
                    _blank(table.c.mpn), _blank(table.c.condition),
                ],
                set_=by_column(ReviewItem, {**fields, "last_seen_at": seen_at}),
            )
            .returning(table.c.id)
        ).one()  # fmt: skip
        return item_id

    def clear(self, session: Session, listing: Listing) -> None:
        """This listing no longer waits for review. What waits of another listing of its page
        still does: saying less is no evidence of being the same product."""
        session.execute(
            delete(ReviewItem).where(
                ReviewItem.store == listing.store,
                ReviewItem.url == listing.url,
                ReviewItem.seller == listing.seller,
                _blank(ReviewItem.mpn) == listing.mpn,
                _blank(ReviewItem.condition) == listing.condition,
            )
        )

    def remember(
        self,
        session: Session,
        listing: Listing,
        *,
        drive_id: UUID | None,
        condition: str | None,
        ignored: bool,
        reviewed_title: str,
    ) -> None:
        """Keep what a reviewer decided a listing is, and the title they decided on, for later
        collected prices of that listing."""
        decision = {
            "drive_id": drive_id, "condition": condition, "ignored": ignored,
            "reviewed_title": reviewed_title,
        }  # fmt: skip
        key = dict(
            zip(("store", "url", "seller", "read_mpn", "read_condition"), listing, strict=True)
        )
        table = ScrapedMatch.__table__
        session.execute(
            pg_insert(table)
            .values(by_column(ScrapedMatch, {**key, **decision}))
            .on_conflict_do_update(
                index_elements=[
                    table.c.source, table.c.url, table.c.seller,
                    table.c.read_mpn, table.c.read_condition,
                ],
                set_=decision,
            )
        )  # fmt: skip

    def claim_decision(
        self, session: Session, item_id: UUID, decision: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Take the decision of an item, held until the operation ends: None when it is the
        first, or what the same decision was answered before (refused when it differs)."""
        claimed = session.scalar(
            pg_insert(ReviewDecision)
            .values(id=item_id, decision=decision)
            .on_conflict_do_nothing(index_elements=[ReviewDecision.id])
            .returning(ReviewDecision.id)
        )
        if claimed is not None:
            return None
        earlier = session.get_one(ReviewDecision, item_id)
        return decided_again(earlier.decision, earlier.result, decision)

    def answer_decision(self, session: Session, item_id: UUID, result: dict[str, Any]) -> None:
        """Keep what an item's decision was answered, to answer it again."""
        session.execute(
            update(ReviewDecision).where(ReviewDecision.id == item_id).values(result=result)
        )

    def peek(self, session: Session, item_id: UUID) -> dict[str, Any]:
        """An item waiting for review, as it is now, without taking it."""
        item = session.get(ReviewItem, item_id)
        if item is None:
            raise ReviewItemNotFound()
        return columns(item)

    def take(self, session: Session, item_id: UUID) -> dict[str, Any]:
        """An item waiting for review, out of the queue: what its page said."""
        item = session.get(ReviewItem, item_id)
        if item is None:
            raise ReviewItemNotFound()
        taken = columns(item)
        session.execute(delete(ReviewItem).where(ReviewItem.id == item_id))
        return taken

    def repoint(self, session: Session, from_drive: UUID, to_drive: UUID) -> None:
        """What waits for review as conflicting with one drive conflicts with another now (the one
        it was merged into), and listings decided to be the one are the other; what was submitted
        is left as it was."""
        session.execute(
            update(ReviewItem)
            .where(ReviewItem.conflict_drive_id == from_drive)
            .values(conflict_drive_id=to_drive)
        )
        session.execute(
            update(ScrapedMatch)
            .where(ScrapedMatch.drive_id == from_drive)
            .values(drive_id=to_drive)
        )
