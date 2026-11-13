"""How the drive service goes about finding, correcting and merging drives: what it asks of its
repositories, in what order, and what it refuses before changing anything. Its repositories and
transactions are stood in for; locks and atomicity are tests/integration's."""

from typing import Any, cast
from uuid import UUID

import pytest

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.drive_service import DriveService
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.review_repository import ReviewRepository
from disktracker.catalog.schemas import DriveEdit, DriveLookup, MergeInput
from disktracker.database import Transactions
from disktracker.errors import DriveNotFound, MergeConflict, SameDrive
from tests.unit.catalog.fakes import FakeDrives, FakeOffers, FakeReviews
from tests.unit.fakes import FakeTransactions

SOURCE, TARGET, KEY = UUID(int=1), UUID(int=2), UUID(int=3)
COLUMNS = {
    "brand": None, "capacity_gb": 18000,
    "specifications": {"media_type": "hdd", "form_factor": "unknown", "interface": "unknown",
                       "recording_type": "unknown", "intended_use": []},
}  # fmt: skip


@pytest.fixture
def transactions() -> FakeTransactions:
    return FakeTransactions()


@pytest.fixture
def drives() -> FakeDrives:
    return FakeDrives(
        drives={
            SOURCE: {**COLUMNS, "id": SOURCE, "mpn": "BBB1", "brand": "Seagate"},
            TARGET: {**COLUMNS, "id": TARGET, "mpn": "AAA1"},
        },
        owners={"AAA1": TARGET, "BBB1": SOURCE},
        identifiers={SOURCE: [{"BBB1", "0XYZ"}], TARGET: [{"AAA1"}]},
    )


@pytest.fixture
def offers() -> FakeOffers:
    return FakeOffers(combined=[(UUID(int=10), UUID(int=20))])


@pytest.fixture
def reviews() -> FakeReviews:
    return FakeReviews()


@pytest.fixture
def subject(
    transactions: FakeTransactions, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews
) -> DriveService:
    return DriveService(
        cast(Transactions, transactions),
        cast(DriveRepository, drives), cast(OfferRepository, offers),
        cast(ReviewRepository, reviews),
    )  # fmt: skip


def merge(subject: DriveService) -> dict[str, Any]:
    return subject.merge(SOURCE, MergeInput(target_drive_id=TARGET), KEY)


class TestMerge:
    def test_a_drive_merged_into_another_is_held_combined_repointed_and_absorbed_in_order(
        self, subject: DriveService, drives: FakeDrives, offers: FakeOffers, reviews: FakeReviews
    ) -> None:
        merged = merge(subject)

        # Every MPN both go by before either drive, then the drives, then their offers and
        # what waits for review.
        assert drives.names() == ["hold", "lock_drives", "absorb"]
        assert drives.of("hold") == [["0XYZ", "AAA1", "BBB1"]]
        assert drives.of("lock_drives") == [[SOURCE, TARGET]]
        assert offers.names() == ["claim", "consolidate", "answer"]
        assert reviews.of("repoint") == [(SOURCE, TARGET)]
        # The target's brand stands where it has one; here it takes the source's.
        [(_, _, values)] = drives.of("absorb")
        assert values["brand"] == "Seagate"
        assert merged == {
            "status": "merged", "drive_id": str(TARGET), "absorbed_drive_id": str(SOURCE),
            "combined_offers": [{"absorbed_offer_id": str(UUID(int=10)), "offer_id": str(UUID(int=20))}],
        }  # fmt: skip

    def test_a_drive_is_not_merged_into_itself_and_its_save_key_is_not_spent(
        self, subject: DriveService, offers: FakeOffers
    ) -> None:
        with pytest.raises(SameDrive):
            subject.merge(TARGET, MergeInput(target_drive_id=TARGET), KEY)

        assert offers.names() == []

    def test_a_merge_sent_again_is_answered_as_it_was_and_merges_nothing(
        self, subject: DriveService, drives: FakeDrives, offers: FakeOffers
    ) -> None:
        offers.replay = {"status": "merged", "drive_id": str(TARGET)}

        assert merge(subject) == offers.replay
        assert drives.names() == []

    def test_what_the_drives_go_by_changing_as_they_are_held_refuses_the_merge(
        self, subject: DriveService, drives: FakeDrives, transactions: FakeTransactions
    ) -> None:
        # Read, then read again once held: another MPN was given the source meanwhile.
        drives.goes_by[SOURCE] = [{"BBB1"}, {"BBB1", "BBB1-X"}]

        with pytest.raises(MergeConflict, match="changed as they were merged"):
            merge(subject)

        assert "absorb" not in drives.names()
        assert not transactions.committed


class TestFind:
    def test_a_drive_is_found_by_an_mpn_it_goes_by_named_by_its_title(
        self, subject: DriveService
    ) -> None:
        found = subject.find(DriveLookup(mpn="aaa1"))

        assert found == {
            "items": [{"drive": {"id": TARGET, "mpn": "AAA1"}, "title": "Title of AAA1"}],
            "total": 1, "limit": 50, "offset": 0,
        }  # fmt: skip

    def test_an_mpn_no_drive_goes_by_finds_none_and_one_past_the_page_finds_none_of_one(
        self, subject: DriveService
    ) -> None:
        assert subject.find(DriveLookup(mpn="CCC1"))["items"] == []
        past = subject.find(DriveLookup(mpn="AAA1", offset=1))
        assert (past["items"], past["total"]) == ([], 1)

    def test_words_find_the_drives_they_name_a_part_at_a_time(
        self, subject: DriveService, drives: FakeDrives
    ) -> None:
        found = subject.find(DriveLookup(q="1", limit=1))

        assert drives.of("named") == [("1", 1, 0)]
        assert (len(found["items"]), found["total"]) == (1, 2)


class TestEdit:
    def test_a_correction_passes_on_only_what_it_gives(
        self, subject: DriveService, drives: FakeDrives, transactions: FakeTransactions
    ) -> None:
        subject.edit(TARGET, DriveEdit.model_validate({"brand": "Seagate"}))
        subject.edit(TARGET, DriveEdit.model_validate({"specifications": {"interface": "sata"}}))

        assert drives.of("correct") == [
            (TARGET, {"brand": "Seagate"}, None),
            (TARGET, {}, {"interface": "sata"}),
        ]
        assert transactions.committed

    def test_a_drive_not_there_is_not_corrected(
        self, subject: DriveService, drives: FakeDrives
    ) -> None:
        with pytest.raises(DriveNotFound):
            subject.edit(UUID(int=99), DriveEdit.model_validate({"brand": "Seagate"}))

        assert drives.of("correct") == []
