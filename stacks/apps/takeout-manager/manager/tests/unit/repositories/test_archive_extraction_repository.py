from __future__ import annotations

import pytest

from backend.db.database import Database
from backend.repositories import ArchiveExtractionRepository


class TestArchiveExtractionRepository:
    @pytest.fixture()
    def db(self) -> Database:
        return Database("sqlite:///:memory:")

    @pytest.fixture()
    def subject(self, db: Database) -> ArchiveExtractionRepository:
        return ArchiveExtractionRepository(session_factory=db.session)

    def test_create_starts_pending(self, subject: ArchiveExtractionRepository) -> None:
        extraction_id = subject.create("takeout-Z-001.tgz")

        record = subject.get_by_id(extraction_id)
        assert record is not None
        assert record.filename == "takeout-Z-001.tgz"
        assert record.status == ArchiveExtractionRepository.PENDING

    def test_get_next_pending_claims_oldest_and_marks_extracting(
        self, subject: ArchiveExtractionRepository
    ) -> None:
        first = subject.create("first.tgz")
        subject.create("second.tgz")

        claimed = subject.get_next_pending()

        assert claimed is not None
        assert claimed.id == first
        assert claimed.status == ArchiveExtractionRepository.EXTRACTING
        # Once claimed it is no longer pending, so the next call yields the second.
        assert subject.get_next_pending().filename == "second.tgz"

    def test_get_next_pending_returns_none_when_empty(
        self, subject: ArchiveExtractionRepository
    ) -> None:
        assert subject.get_next_pending() is None

    def test_update_status_persists(self, subject: ArchiveExtractionRepository) -> None:
        extraction_id = subject.create("takeout-Z-001.tgz")

        subject.update_status(extraction_id, "extracted", "Extracted 10 files")

        record = subject.get_by_id(extraction_id)
        assert record.status == "extracted"
        assert record.message == "Extracted 10 files"
