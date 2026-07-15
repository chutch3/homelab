from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from fiber.db.database import Database
from fiber.repositories.history import HistoryRepository
from fiber.domain.models import Engine, MovementOutcome, MovementRecord
from tests.factories import MovementRecordFactory


def _rec(service: str, minute: int, outcome: MovementOutcome, nbytes: int) -> MovementRecord:
    t = datetime(2026, 6, 15, 3, minute, tzinfo=timezone.utc)
    return MovementRecordFactory.build(
        service=service, started_at=t, finished_at=t, outcome=outcome, bytes_written=nbytes
    )


class TestHistoryRepository:
    @pytest.fixture()
    def subject(self, tmp_path: Path) -> HistoryRepository:
        db = Database(f"sqlite:///{tmp_path}/fiber.db")
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
