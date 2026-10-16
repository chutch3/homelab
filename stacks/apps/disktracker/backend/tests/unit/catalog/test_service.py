"""What the catalog service decides before it asks its repository for a whole operation. The
repository is the service's own port, stood in for by a fake that keeps what it was asked."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest

from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.repository import CatalogRepository
from disktracker.catalog.schemas import DriveEdit, OfferEdit, PriceInput
from disktracker.catalog.service import CatalogService

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


class FakeRepository:
    """Answers every operation with what it was asked, and keeps each call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def record_price(self, *asked: Any) -> dict[str, Any]:
        self.calls.append(("record_price", asked))
        return {"status": "recorded"}

    def edit_drive(self, *asked: Any) -> dict[str, Any]:
        self.calls.append(("edit_drive", asked))
        return {}

    def edit_offer(self, *asked: Any) -> dict[str, Any]:
        self.calls.append(("edit_offer", asked))
        return {}


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def subject(repository: FakeRepository) -> CatalogService:
    return CatalogService(
        cast(CatalogRepository, repository), cast(CatalogQueries, None), now=lambda: NOW
    )


def a_price(**fields: Any) -> PriceInput:
    return PriceInput.model_validate(
        {
            "store": "serverpartdeals",
            "mpn": "ST18000NM000J",
            "condition": "new",
            "title": "Exos X18",
            "url": "https://www.serverpartdeals.com/products/x18",
            "item_price_cents": 1_000_000,
            "shipping_cents": 500,
            **fields,
        }
    )


class TestRecordPrice:
    def test_a_collected_sold_out_price_is_only_a_stock_state(
        self, subject: CatalogService, repository: FakeRepository
    ) -> None:
        """Whatever a store shows while sold out (a placeholder, say) is not a price."""
        subject.record_price(a_price(provenance="collected", in_stock=False), uuid4())

        [(_, (_, price, _, _))] = repository.calls
        assert (price["item_price_cents"], price["shipping_cents"], price["in_stock"]) == (
            None,
            None,
            False,
        )

    @pytest.mark.parametrize(
        "entry",
        [
            {"provenance": "manual", "in_stock": False},
            {"provenance": "collected", "in_stock": True},
        ],
        ids=["entered sold out", "collected in stock"],
    )
    def test_any_other_price_is_recorded_as_given(
        self, subject: CatalogService, repository: FakeRepository, entry: dict[str, Any]
    ) -> None:
        subject.record_price(a_price(**entry), uuid4())

        [(_, (_, price, _, _))] = repository.calls
        assert (price["item_price_cents"], price["shipping_cents"]) == (1_000_000, 500)

    def test_a_key_is_bound_to_what_was_sent_under_it(
        self, subject: CatalogService, repository: FakeRepository
    ) -> None:
        key = uuid4()
        for entry in (a_price(), a_price(), a_price(item_price_cents=999)):
            subject.record_price(entry, key)

        fingerprints = [asked[3] for _, asked in repository.calls]
        assert fingerprints[0] == fingerprints[1] != fingerprints[2]
        assert {asked[2] for _, asked in repository.calls} == {key}


def test_a_drive_correction_passes_on_only_what_it_gives(
    subject: CatalogService, repository: FakeRepository
) -> None:
    drive_id = UUID(int=1)
    subject.edit_drive(drive_id, DriveEdit.model_validate({"brand": "Seagate"}))
    subject.edit_drive(
        drive_id,
        DriveEdit.model_validate({"capacity_gb": 20000, "specifications": {"interface": "sata"}}),
    )

    # Down to each specification: those left out stay as they are.
    assert [asked for _, asked in repository.calls] == [
        (drive_id, {"brand": "Seagate"}, None),
        (drive_id, {"capacity_gb": 20000}, {"interface": "sata"}),
    ]


def test_an_offer_correction_keeps_its_address_as_text(
    subject: CatalogService, repository: FakeRepository
) -> None:
    offer_id = UUID(int=2)
    subject.edit_offer(offer_id, OfferEdit.model_validate({"url": "https://store.test/p/1"}))
    subject.edit_offer(offer_id, OfferEdit.model_validate({"title": "Exos", "url": None}))

    assert [asked for _, asked in repository.calls] == [
        (offer_id, {"url": "https://store.test/p/1"}),
        (offer_id, {"title": "Exos", "url": None}),
    ]
