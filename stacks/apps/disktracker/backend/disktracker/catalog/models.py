"""The catalog's ORM models, over its existing tables: drives, their offers (the listings table)
and prices (observations), the other MPNs a drive goes by, offers waiting for review (unmatched)
and what was decided about scraped ones, the condition rules, and the receipts that make saves
and review decisions retry-safe. Changes to the tables go through Alembic migrations."""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from disktracker.database import Base


class Drive(Base):
    __tablename__ = "drives"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    mpn: Mapped[str] = mapped_column(String(100), unique=True)
    capacity_gb: Mapped[int] = mapped_column(Integer)
    specifications: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    brand: Mapped[str | None] = mapped_column(String(60))


class Offer(Base):
    """One store (and marketplace seller) selling one drive in one condition."""

    __tablename__ = "listings"
    __table_args__ = (
        Index("uq_listings_drive_offer", "drive_id", "store", "seller", "condition", unique=True),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    title: Mapped[str] = mapped_column(String(160))
    store: Mapped[str] = mapped_column(String(20))
    seller: Mapped[str] = mapped_column(String(120))
    url: Mapped[str | None] = mapped_column(Text)
    condition: Mapped[str] = mapped_column(String(40))
    drive_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("drives.id"))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Why it is held out of every ranking, distribution and trend (its page's doubt, as
    # catalog.rules.doubt says) until a person settles what its page is; None for none.
    held_reason: Mapped[str | None] = mapped_column(String(40))


class Price(Base):
    __tablename__ = "observations"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    offer_id: Mapped[uuid.UUID] = mapped_column("listing_id", Uuid, ForeignKey("listings.id"))
    item_price_cents: Mapped[int] = mapped_column(Integer)
    shipping_cents: Mapped[int | None] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean, server_default="true")
    # Who submitted it: manual or collected.
    provenance: Mapped[str] = mapped_column(
        "acquisition_method", String(40), server_default="manual"
    )
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str] = mapped_column(Text)


class MpnAlias(Base):
    __tablename__ = "mpn_aliases"
    alias: Mapped[str] = mapped_column(String(100), primary_key=True)
    drive_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("drives.id"))


class ReviewItem(Base):
    """A listing waiting for a reviewer to say what it is: what one store page said one offer is,
    as it said it. One for each listing (catalog.review_repository.Listing), however many share
    the page."""

    __tablename__ = "unmatched"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    store: Mapped[str] = mapped_column("source", String(40))
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(String(160))
    seller: Mapped[str] = mapped_column(String(120))
    # The MPN and condition as the page gave them, None where it gave none.
    mpn: Mapped[str | None] = mapped_column(String(100))
    condition: Mapped[str | None] = mapped_column(String(40))
    capacity_gb: Mapped[int | None] = mapped_column(Integer)
    # What the page said of the drive; None where it was not kept (items queued before 0037).
    aliases: Mapped[list[str] | None] = mapped_column(JSONB)
    brand: Mapped[str | None] = mapped_column(String(60))
    specifications: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # For an alias conflict: the MPN the page named that another drive goes by, and that drive.
    conflict_mpn: Mapped[str | None] = mapped_column(String(100))
    conflict_drive_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("drives.id", ondelete="SET NULL")
    )
    item_price_cents: Mapped[int | None] = mapped_column(Integer)
    shipping_cents: Mapped[int | None] = mapped_column(Integer)
    in_stock: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str] = mapped_column(String(40))
    provenance: Mapped[str] = mapped_column(String(40))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ScrapedMatch(Base):
    """What a reviewer decided a listing is (the drive and condition it was resolved to, or
    nothing to track), applied to later collected prices of that listing only; with the title it
    was decided on, so that a page that reads otherwise is judged again."""

    __tablename__ = "scraped_matches"
    store: Mapped[str] = mapped_column("source", String(40), primary_key=True)
    url: Mapped[str] = mapped_column(Text, primary_key=True)
    seller: Mapped[str] = mapped_column(String(120), primary_key=True, server_default="")
    # The listing's MPN and condition as read: "" where the page gave none.
    read_mpn: Mapped[str] = mapped_column(String(100), primary_key=True, server_default="")
    read_condition: Mapped[str] = mapped_column(String(40), primary_key=True, server_default="")
    # Gone with its drive: its pages are judged again from what they say next.
    drive_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("drives.id", ondelete="CASCADE")
    )
    condition: Mapped[str | None] = mapped_column(String(40))
    ignored: Mapped[bool] = mapped_column(Boolean, server_default="false")
    reviewed_title: Mapped[str | None] = mapped_column(String(160))


class ConditionRule(Base):
    __tablename__ = "condition_rules"
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    pattern: Mapped[str] = mapped_column(Text)
    condition: Mapped[str] = mapped_column(String(40))


class ReviewDecision(Base):
    """What a reviewer decided about a review item, kept after the item leaves the queue so that
    the same decision sent again is answered as it was the first time."""

    __tablename__ = "review_decisions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    decision: Mapped[dict[str, Any]] = mapped_column(JSONB)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class Receipt(Base):
    """A price submission's Idempotency-Key, what its body was, and what it was answered."""

    __tablename__ = "save_receipts"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    fingerprint: Mapped[str] = mapped_column(String(64))
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
