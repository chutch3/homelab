"""What a price submission is taken to say, what binds its save key to it, and how recording
one goes: the save key, the offer held, the one price writer, the answer kept. Its repositories
and session factory are stood in for; what they do to a database is tests/integration's."""

from typing import Any, cast
from uuid import UUID

import pytest

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.price_service import PriceService, fingerprint, observation
from disktracker.catalog.schemas import PriceInput
from disktracker.database import SessionFactory
from disktracker.errors import DriveNotFound
from tests.unit.catalog.fakes import MADE_PRICE, FakeDrives, FakeOffers, FakeSessions


def a_price(**fields: Any) -> PriceInput:
    """A price a person enters for a drive at a store."""
    return PriceInput.model_validate(
        {
            "drive_id": "22222222-2222-4222-8222-222222222222",
            "store": "serverpartdeals",
            "condition": "new",
            "item_price_cents": 1_000_000,
            "shipping_cents": 500,
            **fields,
        }
    )


def a_recheck(**fields: Any) -> PriceInput:
    """A collector's price of an offer it names, as its page shows it now."""
    return PriceInput.model_validate(
        {
            "offer_id": "11111111-1111-4111-8111-111111111111",
            "provenance": "collected",
            "item_price_cents": 1_000_000,
            "shipping_cents": 500,
            **fields,
        }
    )


def test_a_collected_sold_out_price_is_only_a_stock_state() -> None:
    """Whatever a store shows while sold out (a placeholder, say) is not a price."""
    price = observation(a_recheck(in_stock=False), collected=True)

    assert (price["item_price_cents"], price["shipping_cents"], price["in_stock"]) == (
        None, None, False,
    )  # fmt: skip


@pytest.mark.parametrize(
    ("entry", "collected"),
    [(a_price(in_stock=False), False), (a_recheck(in_stock=True), True)],
    ids=["entered sold out", "collected in stock"],
)
def test_any_other_price_is_recorded_as_given(entry: PriceInput, collected: bool) -> None:
    price = observation(entry, collected)

    assert (price["item_price_cents"], price["shipping_cents"]) == (1_000_000, 500)


def test_a_save_key_is_bound_to_what_was_sent_under_it_and_where() -> None:
    sent = [
        fingerprint("price", a_price()),
        fingerprint("price", a_price()),
        fingerprint("price", a_price(item_price_cents=999)),
        fingerprint("ingestion", a_price()),
    ]

    assert sent[0] == sent[1] != sent[2]
    assert sent[3] != sent[0]


DRIVE, OFFER, KEY = UUID(int=1), UUID(int=2), UUID(int=3)


@pytest.fixture
def sessions() -> FakeSessions:
    return FakeSessions()


@pytest.fixture
def drives() -> FakeDrives:
    return FakeDrives(drives={DRIVE: {"mpn": "ST18000NM000J", "capacity_gb": 18000}})


@pytest.fixture
def offers() -> FakeOffers:
    return FakeOffers(offers={OFFER})


@pytest.fixture
def subject(sessions: FakeSessions, drives: FakeDrives, offers: FakeOffers) -> PriceService:
    return PriceService(
        cast(SessionFactory, sessions), cast(DriveRepository, drives), cast(OfferRepository, offers)
    )


class TestRecord:
    def test_a_save_key_used_before_is_answered_as_it_was_and_nothing_is_recorded(
        self, subject: PriceService, offers: FakeOffers, sessions: FakeSessions
    ) -> None:
        offers.replay = {"status": "recorded", "offer_id": str(OFFER), "price_id": None}

        assert subject.record(a_recheck(offer_id=str(OFFER)), KEY) == offers.replay
        assert offers.names() == ["claim"]
        assert not sessions.committed

    def test_a_price_of_an_offer_named_is_recorded_under_it_held_and_answered(
        self, subject: PriceService, offers: FakeOffers, sessions: FakeSessions
    ) -> None:
        answered = subject.record(a_recheck(offer_id=str(OFFER), in_stock=False), KEY)

        assert offers.names() == ["claim", "lock", "record", "answer"]
        # Collected sold out: a stock state, its price carried on.
        [(_, price, provenance)] = offers.of("record")
        assert (price["item_price_cents"], provenance) == (None, "collected")
        assert answered == {
            "status": "recorded",
            "offer_id": str(OFFER),
            "price_id": str(MADE_PRICE),
        }
        assert offers.of("answer") == [(KEY, answered)]
        assert sessions.committed

    def test_a_price_of_a_drive_is_of_its_offer_at_that_store_from_that_seller(
        self, subject: PriceService, offers: FakeOffers, drives: FakeDrives
    ) -> None:
        subject.record(a_price(drive_id=str(DRIVE), title="Exos", url="https://store.test/x"), KEY)

        assert drives.of("lock_drives") == [[DRIVE]]
        assert offers.of("offer_for") == [((), {
            "drive_id": DRIVE, "store": "serverpartdeals", "seller": "", "condition": "new",
            "title": "Exos", "url": "https://store.test/x",
        })]  # fmt: skip

    def test_a_price_of_a_drive_not_there_is_refused_and_nothing_is_recorded(
        self, subject: PriceService, offers: FakeOffers, sessions: FakeSessions
    ) -> None:
        with pytest.raises(DriveNotFound):
            subject.record(a_price(drive_id=str(UUID(int=99))), KEY)

        assert offers.names() == ["claim"]
        assert not sessions.committed
