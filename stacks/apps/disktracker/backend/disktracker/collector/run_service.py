"""The runs collecting the sources: registered as they start, kept as they go and end, and the
collector heard from, each in one transaction; and what the collector is doing now."""

from typing import Any
from uuid import UUID

from disktracker.clock import Clock
from disktracker.collector.run_repository import RunRepository
from disktracker.collector.schemas import Heartbeat, RunQuery, RunStart, RunUpdate
from disktracker.collector.source_repository import SourceRepository
from disktracker.collector.source_service import in_running_order
from disktracker.database import Transactions


class RunService:
    def __init__(
        self,
        transactions: Transactions,
        runs: RunRepository,
        sources: SourceRepository,
        clock: Clock,
    ) -> None:
        self.transactions, self.runs, self.sources, self.clock = transactions, runs, sources, clock

    def start(self, start: RunStart) -> tuple[dict[str, Any], bool]:
        with self.transactions.begin():
            return self.runs.start(start.model_dump(), self.clock.now())

    def update(self, run_id: UUID, update: RunUpdate) -> dict[str, Any]:
        with self.transactions.begin():
            return self.runs.update(run_id, update.model_dump(), self.clock.now())

    def heartbeat(self, beat: Heartbeat) -> dict[str, Any]:
        with self.transactions.begin():
            now = self.clock.now()
            self.runs.heartbeat(beat.runs, now)
            return {"seen_at": now}

    def listed(self, query: RunQuery) -> list[dict[str, Any]]:
        with self.transactions.begin(reads=True):
            return self.runs.listed(
                query.source, query.status, query.finished_since, query.latest_per_source
            )

    def collector_status(self) -> dict[str, Any]:
        """When a collector was last heard from, the runs in progress, and the sources waiting
        to run, in the order they will: one moment of all three."""
        with self.transactions.begin(reads=True):
            seen, running = self.runs.in_progress()
            busy = {run["source"] for run in running}
            due = in_running_order(self.sources.all(), self.clock.now())
            waiting = [source["key"] for source in due if source["key"] not in busy]
            return {"seen_at": seen, "running": running, "waiting": waiting}
