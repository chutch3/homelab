"""What the run service decides of the collector's status: the sources waiting to run leave out
those already running. Its repositories are stood in for by fakes."""

from datetime import UTC, datetime
from typing import Any, cast

from disktracker.collector.run_repository import RunRepository
from disktracker.collector.run_service import RunService
from disktracker.collector.source_repository import Sourced, SourceRepository
from tests.unit.collector.test_source_service import FakeSources, kept
from tests.unit.fakes import FakeTransactions, FixedClock

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


class FakeRuns:
    """Has never heard from a collector, and has the runs in progress it is given."""

    def __init__(self, *running: dict[str, Any]) -> None:
        self.running = list(running)

    def in_progress(self) -> tuple[datetime | None, list[dict[str, Any]]]:
        return None, self.running


def service(runs: FakeRuns, *sources: Sourced) -> RunService:
    return RunService(
        FakeTransactions(),
        cast(RunRepository, runs),
        cast(SourceRepository, FakeSources(*sources)),
        clock=FixedClock(NOW),
    )


def test_what_is_waiting_leaves_out_sources_already_running() -> None:
    status = service(
        FakeRuns({"source": "busy"}), (kept("Busy"), None), (kept("Idle"), None)
    ).collector_status()

    assert status["waiting"] == ["idle"]
