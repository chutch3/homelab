"""How deciding a review item goes: what is held before the item is taken, what a match records
and remembers (the page's other MPNs attached, or settled when another drive goes by them), and
the queue read with the drives its items name. Its repositories and session factories are stood
in for; locks and atomicity are tests/integration's."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from pydantic import TypeAdapter

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.models import ReviewItem
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.review_repository import ReviewRepository
from disktracker.catalog.review_service import ReviewService
from disktracker.catalog.schemas import ReviewDecision
from disktracker.database import SessionFactory
from disktracker.errors import DriveNotFound
from tests.unit.catalog.fakes import MADE_OFFER, FakeDrives, FakeOffers, FakeReviews, FakeSessions

SEEN = datetime(2026, 10, 1, 12, tzinfo=UTC)
DRIVE, OTHER, ITEM = UUID(int=1), UUID(int=2), UUID(int=3)
URL = "https://www.serverpartdeals.com/products/x18"
WAITING: dict[str, Any] = {
    "store": "serverpartdeals", "url": URL, "seller": "", "mpn": "ST18000NM000J",
    "condition": "new", "title": "Exos X18 18TB", "aliases": ["0FRESH", "0HNHWC"],
    "specifications": None, "brand": "Seagate", "item_price_cents": 30000,
    "shipping_cents": 0, "in_stock": True, "last_seen_at": SEEN, "provenance": "collected",
}  # fmt: skip


def decision(**fields: Any) -> Any:
    return TypeAdapter(ReviewDecision).validate_python(fields)


@pytest.fixture
def sessions() -> FakeSessions:
    return FakeSessions()


@pytest.fixture
def drives() -> FakeDrives:
    return FakeDrives(
        drives={DRIVE: {"mpn": "ST18000NM000J", "capacity_gb": 18000}},
        owners={"ST18000NM000J": DRIVE, "0HNHWC": OTHER},
        identifiers={DRIVE: [{"ST18000NM000J"}]},
    )


@pytest.fixture
def offers() -> FakeOffers:
    return FakeOffers()


@pytest.fixture
def reviews() -> FakeReviews:
    return FakeReviews(items={ITEM: dict(WAITING)})


@pytest.fixture
def subject(
    sessions: FakeSessions, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews
) -> ReviewService:
    return ReviewService(
        cast(SessionFactory, sessions), cast(SessionFactory, sessions),
        cast(DriveRepository, drives), cast(OfferRepository, offers),
        cast(ReviewRepository, reviews),
    )  # fmt: skip


def test_a_match_records_the_page_as_its_drive_and_remembers_what_it_settled(
    subject: ReviewService, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews,
    sessions: FakeSessions,
) -> None:  # fmt: skip
    answered = subject.decide(
        ITEM, decision(decision="match", drive_id=str(DRIVE), condition="new")
    )

    # What the drive goes by and the page's other MPNs, then the drive, before the item.
    assert drives.of("hold") == [["0FRESH", "0HNHWC", "ST18000NM000J"]]
    assert drives.of("lock_drives") == [[DRIVE]]
    assert reviews.names()[:2] == ["claim_decision", "take"]
    assert offers.names() == ["offer_for", "record", "release"]
    # One no drive goes by is the drive's; one another drive goes by stays that drive's.
    assert drives.of("attach_alias") == [(DRIVE, "0FRESH")]
    [(_, remembered)] = reviews.of("remember")
    assert (remembered["drive_id"], remembered["settled_aliases"]) == (DRIVE, ["0HNHWC"])
    assert answered == {"status": "matched", "offer_id": str(MADE_OFFER)}
    assert sessions.committed


def test_an_ignored_item_is_remembered_as_nothing_to_track_and_holds_nothing(
    subject: ReviewService, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews
) -> None:
    answered = subject.decide(ITEM, decision(decision="ignore"))

    assert drives.names() == []
    assert offers.names() == []
    [(_, remembered)] = reviews.of("remember")
    assert (remembered["ignored"], remembered["settled_aliases"]) == (True, [])
    assert answered == {"status": "ignored", "offer_id": None}


def test_a_match_with_a_drive_merged_away_is_refused_before_the_item_is_taken(
    subject: ReviewService, drives: FakeDrives, reviews: FakeReviews, sessions: FakeSessions
) -> None:
    # It went by its MPNs as they were read; held, the drive is gone.
    drives.drives.clear()

    with pytest.raises(DriveNotFound):
        subject.decide(ITEM, decision(decision="match", drive_id=str(DRIVE), condition="new"))

    assert "take" not in reviews.names()
    assert not sessions.committed


def test_a_decision_sent_again_is_answered_as_it_was_and_decides_nothing(
    subject: ReviewService, drives: FakeDrives, reviews: FakeReviews
) -> None:
    reviews.replay = {"status": "ignored", "offer_id": None}

    assert subject.decide(ITEM, decision(decision="ignore")) == reviews.replay
    assert (drives.names(), reviews.names()) == ([], ["claim_decision"])


def test_the_queue_is_read_with_the_drive_each_items_mpn_names(
    subject: ReviewService, reviews: FakeReviews
) -> None:
    named = ReviewItem(id=ITEM, mpn="ST18000NM000J", first_seen_at=SEEN, last_seen_at=SEEN)
    unnamed = ReviewItem(id=UUID(int=4), mpn="0UNKNOWN", first_seen_at=SEEN, last_seen_at=SEEN)
    reviews.queue_read = [named, unnamed]

    items, total = subject.items(None, None, 50, 0)

    assert [item["drive"] for item in items] == [{"id": str(DRIVE), "mpn": "ST18000NM000J"}, None]
    assert total == 2
