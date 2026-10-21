"""What the catalog service decides before it asks its repository for a whole operation. The
repository is the service's own port, stood in for by a fake that keeps what it was asked."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.repository import CatalogRepository
from disktracker.catalog.schemas import OfferEdit
from disktracker.catalog.service import CatalogService

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


class FakeRepository:
    """Answers every operation with what it was asked, and keeps each call."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def record_price(self, *asked: Any) -> dict[str, Any]:
        self.calls.append(("record_price", asked))
        return {"status": "recorded"}

    def edit_offer(self, *asked: Any) -> dict[str, Any]:
        self.calls.append(("edit_offer", asked))
        return {}


@pytest.fixture
def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def subject(repository: FakeRepository) -> CatalogService:
    return CatalogService(
        cast(CatalogRepository, repository),
        cast(CatalogQueries, None),
        now=lambda: NOW,
    )


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
