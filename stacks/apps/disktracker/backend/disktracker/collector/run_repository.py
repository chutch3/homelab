"""The runs collecting the sources, and when the collector was last heard from."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, scoped_session

from disktracker.collector.lifecycle import RESTARTED, SUPERSEDED, abandoned, applies, same_start
from disktracker.collector.models import CONTACT, CollectorContact, CollectorRun, Source
from disktracker.database import columns
from disktracker.errors import RunNotFound, UnknownSource

ZERO = dict.fromkeys(
    ("seen", "recorded", "queued", "ignored", "failed", "rechecked", "recheck_failed"), 0
)


def run_view(run: dict[str, Any], stop_requested_at: datetime | None) -> dict[str, Any]:
    """A run as the API shows it: told to stop when its source was asked since it started."""
    asked = stop_requested_at is not None and stop_requested_at >= run["started_at"]
    return {**run, "id": str(run["id"]), "stop_requested": asked}


class RunRepository:
    def __init__(self, session: scoped_session[Session]) -> None:
        self.session = session

    def start(self, values: dict[str, Any], now: datetime) -> tuple[dict[str, Any], bool]:
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

    def update(self, run_id: UUID, values: dict[str, Any], now: datetime) -> dict[str, Any]:
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
        self.session.execute(
            pg_insert(CollectorContact)
            .values(id=CONTACT, seen_at=now)
            .on_conflict_do_update(index_elements=[CollectorContact.id], set_={"seen_at": now})
        )
        self.session.execute(
            update(CollectorRun)
            .where(CollectorRun.status == "running", CollectorRun.id.not_in(runs))
            .values(**abandoned(RESTARTED, now))
        )

    def listed(
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

    def in_progress(self) -> tuple[datetime | None, list[dict[str, Any]]]:
        """When a collector was last heard from, and the runs in progress, oldest first."""
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
        return seen, running
