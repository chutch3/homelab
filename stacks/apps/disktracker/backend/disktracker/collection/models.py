"""Collection's ORM models, over its existing tables: the stores offers are recorded under, the
runs collecting them, and what a collector last said. Changes go through Alembic migrations."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from disktracker.database import Base


class Source(Base):
    __tablename__ = "sources"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    kind: Mapped[str] = mapped_column(String(20))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    base_url: Mapped[str] = mapped_column(Text)
    schedule: Mapped[str] = mapped_column(String(100))
    enabled: Mapped[bool] = mapped_column(Boolean)
    transport: Mapped[str] = mapped_column(String(20), server_default="direct")
    basis: Mapped[str] = mapped_column(String(20))
    obey_robots: Mapped[bool] = mapped_column(Boolean, server_default="true")
    notes: Mapped[str] = mapped_column(Text)
    run_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stop_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectorRun(Base):
    """One run of one source: running while the collector has it, then completed, failed,
    stopped, or abandoned when the collector no longer has it. Its counts are what it said
    last."""

    __tablename__ = "collector_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    seen: Mapped[int] = mapped_column(Integer)
    recorded: Mapped[int] = mapped_column(Integer)
    queued: Mapped[int] = mapped_column(Integer)
    ignored: Mapped[int] = mapped_column(Integer)
    failed: Mapped[int] = mapped_column(Integer)
    rechecked: Mapped[int] = mapped_column(Integer)
    recheck_failed: Mapped[int] = mapped_column(Integer)
    # Why it did not complete, when known.
    reason: Mapped[str | None] = mapped_column(Text)


# When a collector was last heard from: one row, kept at this id.
CONTACT = 1


class CollectorContact(Base):
    __tablename__ = "collector_contact"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
