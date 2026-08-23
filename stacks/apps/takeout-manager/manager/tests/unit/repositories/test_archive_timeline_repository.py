from __future__ import annotations

import pytest

from backend.db.database import Database
from backend.repositories import ArchiveTimelineRepository


class TestArchiveTimelineRepository:
    @pytest.fixture()
    def db(self) -> Database:
        return Database("sqlite:///:memory:")

    @pytest.fixture()
    def subject(self, db: Database) -> ArchiveTimelineRepository:
        return ArchiveTimelineRepository(session_factory=db.session)

    def test_create_starts_pending(self, subject: ArchiveTimelineRepository) -> None:
        subject.create("takeout-Z-001.tgz")

        record = subject.get_by_filename("takeout-Z-001.tgz")
        assert record is not None
        assert record.status == ArchiveTimelineRepository.PENDING
        assert record.data is None

    def test_get_next_pending_claims_and_marks_processing(
        self, subject: ArchiveTimelineRepository
    ) -> None:
        subject.create("takeout-Z-001.tgz")

        claimed = subject.get_next_pending()

        assert claimed.status == ArchiveTimelineRepository.PROCESSING
        assert subject.get_next_pending() is None  # no longer pending

    def test_upsert_result_completes_an_existing_request(
        self, subject: ArchiveTimelineRepository
    ) -> None:
        subject.create("takeout-Z-001.tgz")

        subject.upsert_result("takeout-Z-001.tgz", '{"2019-07": 10}')

        record = subject.get_by_filename("takeout-Z-001.tgz")
        assert record.status == ArchiveTimelineRepository.COMPLETED
        assert record.data == '{"2019-07": 10}'

    def test_upsert_result_creates_a_row_when_none_requested(
        self, subject: ArchiveTimelineRepository
    ) -> None:
        # The piggyback path has no prior request row.
        subject.upsert_result("takeout-Z-001.tgz", '{"2020-01": 4}')

        record = subject.get_by_filename("takeout-Z-001.tgz")
        assert record.status == ArchiveTimelineRepository.COMPLETED
        assert record.data == '{"2020-01": 4}'

    def test_get_by_filename_returns_the_latest_request(
        self, subject: ArchiveTimelineRepository
    ) -> None:
        subject.create("takeout-Z-001.tgz")
        second = subject.create("takeout-Z-001.tgz")

        assert subject.get_by_filename("takeout-Z-001.tgz").id == second
