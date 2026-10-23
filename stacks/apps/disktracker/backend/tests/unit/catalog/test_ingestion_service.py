"""How taking in a page goes once it is judged (catalog.verdict, tested on its own): what the
service asks of its repositories for each verdict, the drive held before anything of it is read,
and a page foreseen without holding or keeping anything. Its repositories and session factories
are stood in for; locks and atomicity are tests/integration's."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.ingestion_service import CollectedPage, IngestionService
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.review_repository import ReviewRepository
from disktracker.catalog.schemas import IngestionInput
from disktracker.database import SessionFactory
from tests.unit.catalog.fakes import (
    MADE_DRIVE,
    MADE_OFFER,
    MADE_PRICE,
    QUEUED_ITEM,
    FakeDrives,
    FakeOffers,
    FakeReviews,
    FakeSessions,
)

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
DRIVE, OTHER, KEY = UUID(int=1), UUID(int=2), UUID(int=3)
URL = "https://www.serverpartdeals.com/products/x18"
LISTING = ("serverpartdeals", URL, "", "ST18000NM000J", "new")


def page(**fields: Any) -> IngestionInput:
    said = {
        "store": "serverpartdeals", "url": URL, "mpn": "ST18000NM000J", "condition": "new",
        "title": "Seagate Exos X18 ST18000NM000J 18TB", "capacity_gb": 18000,
        "item_price_cents": 30000,
    }  # fmt: skip
    return IngestionInput.model_validate({**said, **fields})


@pytest.fixture
def sessions() -> FakeSessions:
    return FakeSessions()


@pytest.fixture
def drives() -> FakeDrives:
    return FakeDrives(
        drives={DRIVE: {"mpn": "ST18000NM000J", "capacity_gb": 18000}},
        owners={"ST18000NM000J": DRIVE, "0HNHWC": OTHER},
    )


@pytest.fixture
def offers() -> FakeOffers:
    return FakeOffers(priced=True)


@pytest.fixture
def reviews() -> FakeReviews:
    return FakeReviews()


@pytest.fixture
def subject(
    sessions: FakeSessions, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews
) -> IngestionService:
    return IngestionService(
        cast(SessionFactory, sessions), cast(SessionFactory, sessions),
        cast(DriveRepository, drives), cast(OfferRepository, offers),
        cast(ReviewRepository, reviews), now=lambda: NOW,
    )  # fmt: skip


def test_a_page_taken_as_it_reads_is_recorded_its_drive_held_before_it_is_read(
    subject: IngestionService, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews,
    sessions: FakeSessions,
) -> None:  # fmt: skip
    answered = subject.ingest(page(aliases=["0FRESH"], brand="Seagate"), KEY)

    # Every MPN it may touch, then the drive itself, before anything of it is judged.
    assert drives.names()[:2] == ["hold", "lock_drives"]
    assert drives.of("hold") == [["0FRESH", "ST18000NM000J"]]
    assert drives.of("lock_drives") == [[DRIVE]]
    # A known drive keeps its capacity: none is given to register it under.
    assert drives.of("register") == [("ST18000NM000J", 18000)]
    assert drives.of("attach_alias") == [(DRIVE, "0FRESH")]
    assert offers.names() == ["claim", "offer_for", "record", "release", "answer"]
    assert offers.of("release") == [MADE_OFFER]
    assert reviews.of("clear") == [LISTING]
    assert answered == {
        "status": "recorded", "offer_id": str(MADE_OFFER), "price_id": str(MADE_PRICE),
    }  # fmt: skip
    assert sessions.committed


def test_a_new_drive_is_registered_under_the_capacity_its_page_gives(
    subject: IngestionService, drives: FakeDrives
) -> None:
    subject.ingest(page(mpn="ST20000NM007D", capacity_gb=20000, title="Exos X20 20TB"), KEY)

    assert drives.of("lock_drives") == []
    assert drives.of("register") == [("ST20000NM007D", 20000)]
    assert drives.of("describe")[0][0] == MADE_DRIVE


def test_a_doubted_page_waits_for_review_holding_its_drives_offer(
    subject: IngestionService, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews
) -> None:
    answered = subject.ingest(page(title="Seagate Exos X18 ST18000NM000J 18TB 4-pack"), KEY)

    assert offers.of("hold") == [((), {
        "drive_id": DRIVE, "store": "serverpartdeals", "seller": "", "condition": "new",
        "reason": "not_a_single_drive",
    })]  # fmt: skip
    [(listing, fields)] = reviews.of("queue")
    assert (listing, fields["reason"]) == (LISTING, "not_a_single_drive")
    assert "register" not in drives.names()
    assert answered == {"status": "queued", "review_item_id": str(QUEUED_ITEM)}


def test_a_page_naming_another_drives_mpn_waits_whole_naming_that_drive(
    subject: IngestionService, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews
) -> None:
    subject.ingest(page(aliases=["0HNHWC"]), KEY)

    [(_, fields)] = reviews.of("queue")
    assert (fields["reason"], fields["conflict_mpn"], fields["conflict_drive_id"]) == (
        "alias_conflict", "0HNHWC", OTHER,
    )  # fmt: skip
    assert offers.of("hold") == []
    assert "register" not in drives.names()


def test_a_listing_a_reviewer_said_is_nothing_is_ignored_and_nothing_is_held(
    subject: IngestionService, drives: FakeDrives, reviews: FakeReviews, sessions: FakeSessions
) -> None:
    reviews.decided = {"ignored": True, "reviewed_title": "x", "mpn": None, "condition": None}

    assert subject.ingest(page(), KEY) == {"status": "ignored"}
    assert drives.names() == []
    assert sessions.committed


def test_a_save_key_used_before_is_answered_as_it_was_and_nothing_is_taken_in(
    subject: IngestionService, drives: FakeDrives, offers: FakeOffers
) -> None:
    offers.replay = {"status": "queued", "review_item_id": str(QUEUED_ITEM)}

    assert subject.ingest(page(), KEY) == offers.replay
    assert (drives.names(), offers.names()) == ([], ["claim"])


def test_a_page_is_foreseen_as_it_would_be_taken_in_holding_and_keeping_nothing(
    subject: IngestionService, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews,
    sessions: FakeSessions,
) -> None:  # fmt: skip
    foreseen = subject.foresee("serverpartdeals", CollectedPage(
        url=URL, mpn="st18000nm000j", condition="new", title="Exos X18", capacity_gb=20000,
        in_stock=True,
    ))  # fmt: skip

    assert (foreseen.outcome, foreseen.reason) == ("queued", "capacity_conflict")
    assert (drives.names(), offers.names(), reviews.names()) == ([], [], [])
    assert not sessions.committed
