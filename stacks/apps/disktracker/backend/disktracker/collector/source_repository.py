"""The sources offers are collected from, each with when its last run started."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, scoped_session
from sqlalchemy.sql import Select

from disktracker.collector.models import CollectorRun, Source
from disktracker.database import columns
from disktracker.errors import SourceExists, SourceKept, SourceNotFound

# A source as kept, with when its last run started (None: never).
Sourced = tuple[dict[str, Any], datetime | None]


class SourceRepository:
    def __init__(self, session: scoped_session[Session]) -> None:
        self.session = session

    def all(self, by_name: bool = False) -> list[Sourced]:
        """Every source, by name when asked, each with when its last run started."""
        chosen = select(Source).order_by(Source.name) if by_name else select(Source)
        return _with_last_start(self.session, chosen)

    def add(self, values: dict[str, Any]) -> Sourced:
        try:
            source = Source(**values)
            self.session.add(source)
            self.session.flush()
            [added] = _with_last_start(self.session, select(Source).where(Source.id == source.id))
            return added
        except IntegrityError as error:
            raise SourceExists(values["name"]) from error

    def update(self, source_id: UUID, values: dict[str, Any]) -> Sourced:
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

    def delete(self, source_id: UUID) -> None:
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
