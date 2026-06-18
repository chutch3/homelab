from __future__ import annotations

from datetime import datetime, timezone

import pytest

from fiber.database import Database
from fiber.repositories.history import HistoryRepository
from fiber.models import Engine, MovementOutcome, MovementRecord
from tests.factories import MovementRecordFactory


def _rec(service: str, minute: int, outcome: MovementOutcome, nbytes: int) -> MovementRecord:
    t = datetime(2026, 6, 15, 3, minute, tzinfo=timezone.utc)
    return MovementRecordFactory.build(
        service=service, started_at=t, finished_at=t, outcome=outcome, bytes_written=nbytes
    )


class TestHistoryRepository:
    @pytest.fixture()
    def subject(self) -> HistoryRepository:
        db = Database("sqlite:///:memory:")
        return HistoryRepository(session_factory=db.session)

    def test_records_and_reads_last_success(self, subject: HistoryRepository) -> None:
        subject.record(_rec("kenku-pg", 1, MovementOutcome.CLEAN, 100))
        subject.record(_rec("kenku-pg", 2, MovementOutcome.CLOGGED, 0))
        subject.record(_rec("kenku-pg", 3, MovementOutcome.CLEAN, 120))
        last = subject.last_success("kenku-pg")
        assert last == datetime(2026, 6, 15, 3, 3, tzinfo=timezone.utc)

    def test_last_success_none_when_never_clean(self, subject: HistoryRepository) -> None:
        subject.record(_rec("kenku-pg", 1, MovementOutcome.CLOGGED, 0))
        assert subject.last_success("kenku-pg") is None

    def test_median_bytes_of_clean_runs(self, subject: HistoryRepository) -> None:
        for m, b in [(1, 100), (2, 200), (3, 300)]:
            subject.record(_rec("kenku-pg", m, MovementOutcome.CLEAN, b))
        assert subject.median_bytes("kenku-pg", limit=10) == 200

    def test_median_bytes_none_when_no_clean_runs(self, subject: HistoryRepository) -> None:
        assert subject.median_bytes("kenku-pg", limit=10) is None

    def test_last_outcome_returns_most_recent(self, subject: HistoryRepository) -> None:
        subject.record(_rec("kenku-pg", 1, MovementOutcome.CLEAN, 100))
        subject.record(_rec("kenku-pg", 2, MovementOutcome.CLOGGED, 0))
        assert subject.last_outcome("kenku-pg") is MovementOutcome.CLOGGED

    def test_last_outcome_none_when_no_history(self, subject: HistoryRepository) -> None:
        assert subject.last_outcome("kenku-pg") is None

    def test_recent_returns_most_recent_first(self, subject: HistoryRepository) -> None:
        subject.record(_rec("kenku-pg", 1, MovementOutcome.CLEAN, 100))
        subject.record(_rec("kenku-pg", 2, MovementOutcome.CLOGGED, 0))
        subject.record(_rec("kenku-pg", 3, MovementOutcome.CLEAN, 120))
        rows = subject.recent("kenku-pg", limit=5)
        assert len(rows) == 3
        assert rows[0].outcome is MovementOutcome.CLEAN
        assert rows[0].bytes_written == 120  # minute=3, most recent first

    def test_recent_honours_limit(self, subject: HistoryRepository) -> None:
        for m in range(10):
            subject.record(_rec("kenku-pg", m, MovementOutcome.CLEAN, 100))
        rows = subject.recent("kenku-pg", limit=5)
        assert len(rows) == 5

    def test_recent_returns_empty_for_unknown_service(self, subject: HistoryRepository) -> None:
        rows = subject.recent("ghost", limit=5)
        assert rows == []

    def test_recent_returns_full_movement_records(self, subject: HistoryRepository) -> None:
        from fiber.models import Engine
        subject.record(_rec("kenku-pg", 1, MovementOutcome.CLOGGED, 0))
        rows = subject.recent("kenku-pg", limit=5)
        assert rows[0].service == "kenku-pg"
        assert isinstance(rows[0].engine, Engine)

    def test_latest_clean_returns_most_recent_clean_record(self, subject: HistoryRepository) -> None:
        subject.record(_rec("kenku-pg", 1, MovementOutcome.CLEAN, 100))
        subject.record(_rec("kenku-pg", 2, MovementOutcome.CLOGGED, 0))
        subject.record(_rec("kenku-pg", 3, MovementOutcome.CLEAN, 300))
        rec = subject.latest_clean("kenku-pg")
        assert rec is not None
        assert rec.outcome is MovementOutcome.CLEAN
        assert rec.bytes_written == 300

    def test_latest_clean_returns_none_when_no_clean_rows(self, subject: HistoryRepository) -> None:
        subject.record(_rec("kenku-pg", 1, MovementOutcome.CLOGGED, 0))
        assert subject.latest_clean("kenku-pg") is None

    def test_latest_clean_returns_none_for_unknown_service(self, subject: HistoryRepository) -> None:
        assert subject.latest_clean("ghost") is None
