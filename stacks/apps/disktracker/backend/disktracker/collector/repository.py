"""The sources offers are collected from, their runs, and when the collector was last heard
from."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session
from sqlalchemy.sql import Select

from disktracker.collector.lifecycle import RESTARTED, SUPERSEDED, abandoned, applies, same_start
from disktracker.collector.models import (
    CONTACT,
    CollectorContact,
    CollectorRun,
    Source,
)
from disktracker.database import columns
from disktracker.errors import (
    RunNotFound,
    SourceExists,
    SourceKept,
    SourceNotFound,
    UnknownSource,
)

# A source as kept, with when its last run started (None: never).
Sourced = tuple[dict[str, Any], datetime | None]


ZERO = dict.fromkeys(
    ("seen", "recorded", "queued", "ignored", "failed", "rechecked", "recheck_failed"), 0
)


def run_view(run: dict[str, Any], stop_requested_at: datetime | None) -> dict[str, Any]:
    """A run as the API shows it: told to stop when its source was asked since it started."""
    asked = stop_requested_at is not None and stop_requested_at >= run["started_at"]
    return {**run, "id": str(run["id"]), "stop_requested": asked}


class CollectionRepository:
    def __init__(self, session: scoped_session[Session]) -> None:
        self.session = session

    def sources(self, by_name: bool = False) -> list[Sourced]:
        """Every source, by name when asked, each with when its last run started."""
        chosen = select(Source).order_by(Source.name) if by_name else select(Source)
        return _with_last_start(self.session, chosen)

    def add_source(self, values: dict[str, Any]) -> Sourced:
        try:
            source = Source(**values)
            self.session.add(source)
            self.session.flush()
            [added] = _with_last_start(self.session, select(Source).where(Source.id == source.id))
            return added
        except IntegrityError as error:
            raise SourceExists(values["name"]) from error

    def update_source(self, source_id: UUID, values: dict[str, Any]) -> Sourced:
        """Change a source, by what is given; SourceNotFound when there is no such source."""
        try:
            changed = self.session.execute(
                update(Source).where(Source.id == source_id).values(**values)
            ).rowcount
            if not changed:
                raise SourceNotFound()
            [updated] = _with_last_start(self.session, select(Source).where(Source.id == source_id))
            return updated
        except IntegrityError as error:
            raise SourceExists(values.get("name", "")) from error

    def delete_source(self, source_id: UUID) -> None:
        """Delete a source nothing is recorded under; its runs and what was decided about its
        listings go with it. One with offers or listings waiting for review is kept, and so is
        Other."""
        key = self.session.scalar(select(Source.key).where(Source.id == source_id))
        if key is None:
            raise SourceNotFound()
        if key == "other":
            raise SourceKept("Other is always kept, for one-off stores.")
        try:
            self.session.execute(delete(Source).where(Source.id == source_id))
        except IntegrityError as error:
            raise SourceKept(
                "Offers are recorded under this source. Switch it off instead."
            ) from error

    def start_run(self, values: dict[str, Any], now: datetime) -> tuple[dict[str, Any], bool]:
        """Register a run as it starts, and whether it is new: the same start sent again is
        the run already registered; another under its id is refused. A run of the source still
        marked running is abandoned, since its collector no longer has it."""
        source = self.session.scalars(
            select(Source).where(Source.key == values["source"]).with_for_update()
        ).first()
        if source is None:
            raise UnknownSource()
        created = self.session.scalar(
            pg_insert(CollectorRun)
            .values(**values, status="running", updated_at=now, **ZERO)
            .on_conflict_do_nothing(index_elements=[CollectorRun.id])
            .returning(CollectorRun.id)
        )
        run = self.session.get_one(CollectorRun, values["id"])
        if created is None:
            same_start(columns(run), values)
            return run_view(columns(run), source.stop_requested_at), False
        self.session.execute(
            update(CollectorRun)
            .where(
                CollectorRun.source == run.source,
                CollectorRun.status == "running",
                CollectorRun.id != run.id,
            )
            .values(**abandoned(SUPERSEDED, now))
        )
        return run_view(columns(run), source.stop_requested_at), True

    def update_run(self, run_id: UUID, values: dict[str, Any], now: datetime) -> dict[str, Any]:
        """Keep how far a running run has got, or how it ended. A run that has ended stays as
        it ended: the same end sent again changes nothing, and anything else is refused."""
        run = self.session.scalars(
            select(CollectorRun).where(CollectorRun.id == run_id).with_for_update()
        ).first()
        if run is None:
            raise RunNotFound()
        kept = {key: getattr(run, key) for key in values}
        if applies(run.status, kept, values):
            for key, value in values.items():
                setattr(run, key, value)
            run.updated_at = now
            self.session.flush()
        asked = self.session.scalar(
            select(Source.stop_requested_at).where(Source.key == run.source)
        )
        return run_view(columns(run), asked)

    def heartbeat(self, runs: list[UUID], now: datetime) -> None:
        """The collector is alive, with these runs: any other still marked running is
        abandoned."""
        _heard(self.session, now)
        self.session.execute(
            update(CollectorRun)
            .where(CollectorRun.status == "running", CollectorRun.id.not_in(runs))
            .values(**abandoned(RESTARTED, now))
        )

    def runs(
        self,
        source: str | None,
        status: str | None,
        finished_since: datetime | None,
        latest_per_source: bool,
    ) -> list[dict[str, Any]]:
        """Runs oldest first, of a source, in a status, ended since a moment; or the latest run
        of each source, by source."""
        chosen = select(CollectorRun, Source.stop_requested_at).outerjoin(
            Source, Source.key == CollectorRun.source
        )
        if source is not None:
            chosen = chosen.where(CollectorRun.source == source)
        if status is not None:
            chosen = chosen.where(CollectorRun.status == status)
        if finished_since is not None:
            chosen = chosen.where(CollectorRun.finished_at >= finished_since)
        if latest_per_source:
            chosen = chosen.distinct(CollectorRun.source).order_by(
                CollectorRun.source, CollectorRun.started_at.desc()
            )
        else:
            chosen = chosen.order_by(CollectorRun.started_at, CollectorRun.id)
        return [
            run_view(columns(run), asked) for run, asked in self.session.execute(chosen).tuples()
        ]

    def collector_status(self) -> tuple[datetime | None, list[dict[str, Any]], list[Sourced]]:
        """When a collector was last heard from, the runs in progress, and every source with
        when its last run started: one moment of all three."""
        seen = self.session.scalar(select(CollectorContact.seen_at))
        running = [
            run_view(columns(run), asked)
            for run, asked in self.session.execute(
                select(CollectorRun, Source.stop_requested_at)
                .outerjoin(Source, Source.key == CollectorRun.source)
                .where(CollectorRun.status == "running")
                .order_by(CollectorRun.started_at)
            ).tuples()
        ]
        return seen, running, _with_last_start(self.session, select(Source))


def _with_last_start(session: Session, chosen: Select[Any]) -> list[Sourced]:
    """The chosen sources, each with when its last run started, in one query."""
    last_runs = (
        select(CollectorRun.source, func.max(CollectorRun.started_at).label("last"))
        .group_by(CollectorRun.source)
        .subquery()
    )
    rows = session.execute(
        chosen.add_columns(last_runs.c.last).outerjoin(last_runs, last_runs.c.source == Source.key)
    )
    return [(columns(source), last) for source, last in rows.tuples()]


def _heard(session: Session, now: datetime) -> None:
    session.execute(
        pg_insert(CollectorContact)
        .values(id=CONTACT, seen_at=now)
        .on_conflict_do_update(index_elements=[CollectorContact.id], set_={"seen_at": now})
    )
