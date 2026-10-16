"""Reporting's ORM models, over its existing tables. Changes go through Alembic migrations."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from disktracker.database import Base


class Trend(Base):
    """A trend once worked out: by is the split, empty for none; stamp, the prices it stands for;
    revision, the past it was worked out from."""

    __tablename__ = "trends"
    days: Mapped[int] = mapped_column(Integer, primary_key=True)
    by: Mapped[str] = mapped_column(String(20), primary_key=True)
    recent_days: Mapped[int] = mapped_column(Integer, primary_key=True)
    # The drives it is of: DriveScope.key(), empty for every drive.
    scope: Mapped[str] = mapped_column(Text, primary_key=True, server_default="")
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stamp: Mapped[str] = mapped_column(Text)
    revision: Mapped[int | None] = mapped_column(BigInteger)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)


class HistoryRevision(Base):
    """One row, counted up by the database whenever the past a trend reads changes: a price
    changed or removed, an offer moved to another drive, store or condition or removed, or a
    drive's capacity changed or the drive removed. Recording a new price or a check does not."""

    __tablename__ = "history_revision"
    id: Mapped[bool] = mapped_column(Boolean, primary_key=True)
    revision: Mapped[int] = mapped_column(BigInteger)
