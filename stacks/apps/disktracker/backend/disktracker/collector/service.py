"""Collection's workflows: the stores offers are collected from, when each is due, the runs
collecting them, and trying a store before it is collected. It applies what each request means,
each in one transaction, and asks its repository for what is kept."""

import re
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from croniter import croniter

from disktracker.clock import Clock
from disktracker.collector.repository import CollectionRepository, Sourced
from disktracker.collector.schemas import (
    Heartbeat,
    RunQuery,
    RunStart,
    RunUpdate,
    SourceBase,
)
from disktracker.collector.settings import KINDS
from disktracker.database import Transactions


def due_at(source: dict[str, Any], last_started: datetime | None, now: datetime) -> datetime | None:
    """When a source is next due: never, for a store entered by hand; when it was asked to
    run, if no run has started since; otherwise, while it is switched on, the first time its
    schedule fires after its last run started, or now if it has never run."""
    if source["kind"] == "manual":
        return None
    requested = source["run_requested_at"]
    if requested is not None and (last_started is None or requested > last_started):
        return cast(datetime, requested)
    if not source["enabled"]:
        return None
    if last_started is None:
        return now
    return cast(datetime, croniter(source["schedule"], last_started).get_next(datetime))


def source_key(name: str) -> str:
    """What a source's offers, prices and runs are recorded under: its name's letters and
    digits, in lower case."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


class CollectionService:
    def __init__(
        self,
        transactions: Transactions,
        repository: CollectionRepository,
        clock: Clock,
    ) -> None:
        self.transactions, self.repository, self.clock = transactions, repository, clock

    def _view(self, sourced: Sourced, now: datetime) -> tuple[dict[str, Any], bool]:
        """A source as the API shows it, with when it is next due as of now, and whether that
        is because it was asked to run."""
        source, last_started = sourced
        due = due_at(source, last_started, now)
        asked = due is not None and due == source["run_requested_at"]
        shown = {
            key: value
            for key, value in source.items()
            if key not in ("run_requested_at", "stop_requested_at")
        }
        shown["settings"] = KINDS[source["kind"]].settings.saved(source["settings"])
        return {**shown, "id": str(source["id"]), "next_run_at": due}, asked

    def _due(self, sources: list[Sourced]) -> list[dict[str, Any]]:
        """The sources due to run now, in the order to run them: those asked to run, in the
        order they were asked, ahead of those whose schedule has fired, most overdue first."""
        now = self.clock.now()
        due = [
            (not asked, source["next_run_at"], source)
            for source, asked in (self._view(sourced, now) for sourced in sources)
            if source["next_run_at"] is not None and source["next_run_at"] <= now
        ]
        return [source for *_, source in sorted(due, key=lambda entry: entry[:2])]

    def list_sources(self) -> list[dict[str, Any]]:
        with self.transactions.begin(reads=True):
            now = self.clock.now()
            return [
                self._view(sourced, now)[0] for sourced in self.repository.sources(by_name=True)
            ]

    def due_sources(self) -> list[dict[str, Any]]:
        with self.transactions.begin(reads=True):
            return self._due(self.repository.sources())

    def add_source(self, entry: SourceBase) -> dict[str, Any]:
        with self.transactions.begin():
            values = {"key": source_key(entry.name), **entry.model_dump()}
            return self._view(self.repository.add_source(values), self.clock.now())[0]

    def update_source(self, source_id: UUID, entry: SourceBase) -> dict[str, Any]:
        with self.transactions.begin():
            updated = self.repository.update_source(source_id, entry.model_dump())
            return self._view(updated, self.clock.now())[0]

    def request_run(self, source_id: UUID) -> dict[str, Any]:
        with self.transactions.begin():
            updated = self.repository.update_source(
                source_id, {"run_requested_at": self.clock.now()}
            )
            return self._view(updated, self.clock.now())[0]

    def request_stop(self, source_id: UUID) -> dict[str, Any]:
        """Ask the source's run in progress to stop; it is told the next time it says how far
        it has got. A run that starts later is not stopped by it."""
        with self.transactions.begin():
            updated = self.repository.update_source(
                source_id, {"stop_requested_at": self.clock.now()}
            )
            return self._view(updated, self.clock.now())[0]

    def delete_source(self, source_id: UUID) -> None:
        """Delete a source nothing is recorded under, with its runs and what it was told about
        scraped offers. One with offers, or queued offers, is kept, and so is Other."""
        with self.transactions.begin():
            self.repository.delete_source(source_id)

    def start_run(self, start: RunStart) -> tuple[dict[str, Any], bool]:
        with self.transactions.begin():
            return self.repository.start_run(start.model_dump(), self.clock.now())

    def update_run(self, run_id: UUID, update: RunUpdate) -> dict[str, Any]:
        with self.transactions.begin():
            return self.repository.update_run(run_id, update.model_dump(), self.clock.now())

    def heartbeat(self, beat: Heartbeat) -> dict[str, Any]:
        with self.transactions.begin():
            now = self.clock.now()
            self.repository.heartbeat(beat.runs, now)
            return {"seen_at": now}

    def runs(self, query: RunQuery) -> list[dict[str, Any]]:
        with self.transactions.begin(reads=True):
            return self.repository.runs(
                query.source, query.status, query.finished_since, query.latest_per_source
            )

    def collector_status(self) -> dict[str, Any]:
        """When a collector was last heard from, the runs in progress, and the sources waiting
        to run, in the order they will."""
        with self.transactions.begin(reads=True):
            seen, running, sources = self.repository.collector_status()
            busy = {run["source"] for run in running}
            waiting = [source["key"] for source in self._due(sources) if source["key"] not in busy]
            return {"seen_at": seen, "running": running, "waiting": waiting}
