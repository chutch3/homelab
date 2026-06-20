from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.engine import Engine
from sqlmodel import Field, Session, SQLModel, delete, select

from warden.models import Anchor


class QueueProgressRow(SQLModel, table=True):
    __tablename__ = "queue_progress"
    download_id: str = Field(primary_key=True)
    size_left: int = Field(default=0)
    at_epoch: float = Field(default=0.0)   # anchor time as unix seconds (tz-safe)


class QueueProgressRepository:
    """Persists the no-progress anchor per downloadId across ticks (survives restarts)."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def snapshot(self) -> dict[str, Anchor]:
        with Session(self._engine) as session:
            rows = session.exec(select(QueueProgressRow)).all()
            return {
                r.download_id: Anchor(r.size_left, datetime.fromtimestamp(r.at_epoch, tz=timezone.utc))
                for r in rows
            }

    def replace(self, state: dict[str, Anchor]) -> None:
        with Session(self._engine) as session:
            session.exec(delete(QueueProgressRow))
            for did, a in state.items():
                session.add(QueueProgressRow(download_id=did, size_left=a.size_left,
                                             at_epoch=a.at.timestamp()))
            session.commit()
