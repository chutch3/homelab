"""What the catalog service decides before it asks its repository for a whole operation. The
repository is the service's own port, stood in for by a fake that keeps what it was asked."""

from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.repository import CatalogRepository
from disktracker.catalog.schemas import DriveEdit, OfferEdit
from disktracker.catalog.service import CatalogService
from disktracker.database import SessionFactory

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
    # Making a drive is the drive repository's, tested against the database
    # (tests/integration/test_drives.py); nothing here makes one.
    return CatalogService(
        cast(CatalogRepository, repository),
        cast(CatalogQueries, None),
        now=lambda: NOW,
        session_factory=cast(SessionFactory, None),
        drives=cast(DriveRepository, None),
    )


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
