from __future__ import annotations

from collections.abc import Iterable, Mapping

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, select


class SearchBackoffRow(SQLModel, table=True):
    __tablename__ = "search_backoff"
    source: str = Field(primary_key=True)
    remote_id: int = Field(primary_key=True)
    miss_streak: int = Field(default=0)
    until_epoch: float = Field(default=0.0)   # cooldown expiry (unix s); 0.0 = not backed off


class SearchBackoffRepository:
    """Persists per-item miss streaks + cooldown expiries that gate hunting (survives restarts)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def streaks(self, source: str, ids: Iterable[int]) -> dict[int, int]:
        ids = list(ids)
        if not ids:
            return {}
        with Session(self._engine) as session:
            rows = session.exec(
                select(SearchBackoffRow).where(SearchBackoffRow.source == source,
                                               SearchBackoffRow.remote_id.in_(ids))).all()
            return {r.remote_id: r.miss_streak for r in rows}

    def write(self, source: str, clear: Iterable[int],
              upsert: Mapping[int, tuple[int, float]]) -> None:
        with Session(self._engine) as session:
            for remote_id in clear:
                row = session.get(SearchBackoffRow, (source, remote_id))
                if row is not None:
                    session.delete(row)
            for remote_id, (streak, until) in upsert.items():
                row = session.get(SearchBackoffRow, (source, remote_id))
                if row is None:
                    row = SearchBackoffRow(source=source, remote_id=remote_id)
                row.miss_streak = streak
                row.until_epoch = until
                session.add(row)
            session.commit()

    def active(self, source: str, now_epoch: float) -> set[int]:
        with Session(self._engine) as session:
            rows = session.exec(
                select(SearchBackoffRow.remote_id).where(
                    SearchBackoffRow.source == source,
                    SearchBackoffRow.until_epoch > now_epoch)).all()
            return set(rows)

    def count_active(self, source: str, now_epoch: float) -> int:
        return len(self.active(source, now_epoch))
