"""Reporting's ORM models, over its existing tables. Changes go through Alembic migrations."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from disktracker.database import Base


class Trend(Base):
    """A trend once worked out: by is the split, empty for none; revision, that of what it was
    worked out from (TrendRevision)."""

    __tablename__ = "trends"
    days: Mapped[int] = mapped_column(Integer, primary_key=True)
    by: Mapped[str] = mapped_column(String(20), primary_key=True)
    recent_days: Mapped[int] = mapped_column(Integer, primary_key=True)
    # The drives it is of: reporting.reporting_service.kept_as, empty for every drive.
    scope: Mapped[str] = mapped_column(Text, primary_key=True, server_default="")
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revision: Mapped[int] = mapped_column(BigInteger)
    body: Mapped[dict[str, Any]] = mapped_column(JSONB)


class TrendRevision(Base):
    """One row, counted up by the database once for each piece of work that changes anything a
    trend reads: a price, an offer, a drive, a drive's other MPNs, or a store's name (migration
    0035 lists them)."""

    __tablename__ = "trend_revision"
    id: Mapped[bool] = mapped_column(Boolean, primary_key=True)
    revision: Mapped[int] = mapped_column(BigInteger)
