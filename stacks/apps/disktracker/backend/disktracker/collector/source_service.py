"""The stores offers are collected from: kept, changed and removed, asked to run or stop, and
when each is due, each in one transaction."""

import re
from datetime import datetime
from typing import Any, cast
from uuid import UUID

from croniter import croniter

from disktracker.clock import Clock
from disktracker.collector.schemas import SourceBase
from disktracker.collector.settings import KINDS
from disktracker.collector.source_repository import Sourced, SourceRepository
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


def shown(sourced: Sourced, now: datetime) -> tuple[dict[str, Any], bool]:
    """A source as the API shows it, with when it is next due as of now, and whether that is
    because it was asked to run."""
    source, last_started = sourced
    due = due_at(source, last_started, now)
    asked = due is not None and due == source["run_requested_at"]
    view = {
        key: value
        for key, value in source.items()
        if key not in ("run_requested_at", "stop_requested_at")
    }
    view["settings"] = KINDS[source["kind"]].settings.saved(source["settings"])
    return {**view, "id": str(source["id"]), "next_run_at": due}, asked


def in_running_order(sources: list[Sourced], now: datetime) -> list[dict[str, Any]]:
    """The sources due to run now, in the order to run them: those asked to run, in the order
    they were asked, ahead of those whose schedule has fired, most overdue first."""
    due = [
        (not asked, source["next_run_at"], source)
        for source, asked in (shown(sourced, now) for sourced in sources)
        if source["next_run_at"] is not None and source["next_run_at"] <= now
    ]
    return [source for *_, source in sorted(due, key=lambda entry: entry[:2])]


class SourceService:
    def __init__(self, transactions: Transactions, sources: SourceRepository, clock: Clock) -> None:
        self.transactions, self.sources, self.clock = transactions, sources, clock

    def listed(self) -> list[dict[str, Any]]:
        with self.transactions.begin(reads=True):
            now = self.clock.now()
            return [shown(sourced, now)[0] for sourced in self.sources.all(by_name=True)]

    def due(self) -> list[dict[str, Any]]:
        with self.transactions.begin(reads=True):
            return in_running_order(self.sources.all(), self.clock.now())

    def add(self, entry: SourceBase) -> dict[str, Any]:
        with self.transactions.begin():
            values = {"key": source_key(entry.name), **entry.model_dump()}
            return shown(self.sources.add(values), self.clock.now())[0]

    def update(self, source_id: UUID, entry: SourceBase) -> dict[str, Any]:
        with self.transactions.begin():
            return shown(self.sources.update(source_id, entry.model_dump()), self.clock.now())[0]

    def request_run(self, source_id: UUID) -> dict[str, Any]:
        with self.transactions.begin():
            updated = self.sources.update(source_id, {"run_requested_at": self.clock.now()})
            return shown(updated, self.clock.now())[0]

    def request_stop(self, source_id: UUID) -> dict[str, Any]:
        """Ask the source's run in progress to stop; it is told the next time it says how far
        it has got. A run that starts later is not stopped by it."""
        with self.transactions.begin():
            updated = self.sources.update(source_id, {"stop_requested_at": self.clock.now()})
            return shown(updated, self.clock.now())[0]

    def delete(self, source_id: UUID) -> None:
        """Delete a source nothing is recorded under, with its runs and what it was told about
        scraped offers. One with offers, or queued offers, is kept, and so is Other."""
        with self.transactions.begin():
            self.sources.delete(source_id)
