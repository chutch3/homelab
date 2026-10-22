"""How offers and their prices are corrected: what is given passed on as it is kept, and a price
removed with its offer only when it was the offer's last. Its repository and session factories
are stood in for; locks and atomicity are tests/integration's."""

from typing import cast
from uuid import UUID

import pytest

from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.offer_service import OfferService
from disktracker.catalog.schemas import OfferEdit
from disktracker.database import SessionFactory
from disktracker.errors import OfferNotFound
from tests.unit.catalog.fakes import FakeOffers, FakeSessions

OFFER, LAST, ANOTHER = UUID(int=1), UUID(int=2), UUID(int=3)


@pytest.fixture
def sessions() -> FakeSessions:
    return FakeSessions()


@pytest.fixture
def offers() -> FakeOffers:
    # Two prices of one offer: one its last, one with another beside it.
    return FakeOffers(offers={OFFER}, prices={LAST: (OFFER, False), ANOTHER: (OFFER, True)})


@pytest.fixture
def subject(sessions: FakeSessions, offers: FakeOffers) -> OfferService:
    return OfferService(
        cast(SessionFactory, sessions),
        cast(SessionFactory, sessions),
        cast(OfferRepository, offers),
    )


def test_an_offer_correction_keeps_its_address_as_text_and_passes_on_only_what_it_gives(
    subject: OfferService, offers: FakeOffers, sessions: FakeSessions
) -> None:
    subject.edit(OFFER, OfferEdit.model_validate({"url": "https://store.test/p/1"}))
    subject.edit(OFFER, OfferEdit.model_validate({"title": "Exos", "url": None}))

    assert offers.of("edit") == [
        (OFFER, {"url": "https://store.test/p/1"}),
        (OFFER, {"title": "Exos", "url": None}),
    ]
    assert sessions.committed


def test_an_offer_not_there_is_not_corrected(subject: OfferService, offers: FakeOffers) -> None:
    with pytest.raises(OfferNotFound):
        subject.edit(UUID(int=99), OfferEdit.model_validate({"title": "Exos"}))

    assert offers.of("edit") == []


def test_a_price_removed_takes_its_offer_with_it_only_when_it_was_the_last(
    subject: OfferService, offers: FakeOffers
) -> None:
    subject.delete_price(ANOTHER)
    assert offers.of("delete") == []

    subject.delete_price(LAST)
    assert offers.of("delete") == [OFFER]


def test_a_price_not_there_is_already_removed(
    subject: OfferService, offers: FakeOffers, sessions: FakeSessions
) -> None:
    subject.delete_price(UUID(int=99))

    assert offers.names() == []
    assert not sessions.committed
