from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, select

from warden.models import SearchAttempt


class SearchAttemptRow(SQLModel, table=True):
    __tablename__ = "search_attempt"
    source: str = Field(primary_key=True)
    remote_id: int = Field(primary_key=True)
    kind: str = Field(default="missing")
    searched_at_epoch: float = Field(default=0.0)   # unix seconds (tz-safe)


class SearchAttemptRepository:
    """Persists searches awaiting reconciliation against grabs (survives restarts)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def pending(self, source: str) -> list[SearchAttempt]:
        with Session(self._engine) as session:
            rows = session.exec(select(SearchAttemptRow).where(SearchAttemptRow.source == source)).all()
            return [
                SearchAttempt(remote_id=r.remote_id, kind=r.kind,
                              searched_at=datetime.fromtimestamp(r.searched_at_epoch, tz=timezone.utc))
                for r in rows
            ]

    def record(self, source: str, items: Iterable[tuple[int, str]], at: datetime) -> None:
        epoch = at.timestamp()
        with Session(self._engine) as session:
            for remote_id, kind in items:
                row = session.get(SearchAttemptRow, (source, remote_id))
                if row is None:
                    row = SearchAttemptRow(source=source, remote_id=remote_id)
                row.kind = kind
                row.searched_at_epoch = epoch
                session.add(row)
            session.commit()

    def drop(self, source: str, remote_ids: Iterable[int]) -> None:
        ids = list(remote_ids)
        if not ids:
            return
        with Session(self._engine) as session:
            for remote_id in ids:
                row = session.get(SearchAttemptRow, (source, remote_id))
                if row is not None:
                    session.delete(row)
            session.commit()

    def count(self, source: str) -> int:
        return len(self.pending(source))
