"""Listings waiting for review, and what reviewers decided listings are. Each method works on the
session of the operation that calls it and never commits: the operation decides what is kept
together."""

from collections.abc import Callable
from datetime import datetime
from typing import Any, NamedTuple, Self
from uuid import UUID

from sqlalchemy import delete, func, literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from disktracker.catalog.models import ReviewItem, ScrapedMatch
from disktracker.database import by_column, columns


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


class ReviewRepository:
    def __init__(self, next_id: Callable[[], UUID]) -> None:
        self.next_id = next_id

    def decision_for(self, session: Session, listing: Listing) -> dict[str, Any] | None:
        """What a reviewer decided this listing is, if one has; no other listing's decision,
        though it shares the page."""
        decided = session.get(ScrapedMatch, tuple(listing))
        return None if decided is None else columns(decided)

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
        mpn: str | None,
        condition: str | None,
        ignored: bool,
        reviewed_title: str,
    ) -> None:
        """Keep what a reviewer decided a listing is, and the title they decided on, for later
        collected prices of that listing."""
        decision = {
            "mpn": mpn, "condition": condition, "ignored": ignored,
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
