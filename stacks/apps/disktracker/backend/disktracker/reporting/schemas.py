"""Reporting's public contract: what its routes return."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from disktracker.catalog.schemas import Condition, DriveScope
from disktracker.contract import Contract

# The days a trend can look back over.
PERIODS = (7, 14, 30, 90, 180)


class TrendQuery(DriveScope):
    """A trend over the days asked for, split when asked, of the drives asked for (every drive
    unless narrowed as the drives list is). recent_days: an offer unchecked for longer is taken
    to have ended at its last check."""

    model_config = ConfigDict(extra="forbid")
    days: int = Field(
        default=90,
        description="How far back to look, in days.",
        json_schema_extra={"enum": list(PERIODS)},
    )
    by: Literal["condition", "capacity", "store"] | None = None
    recent_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="An offer unchecked for longer is treated as ending at its last check.",
    )

    @field_validator("days")
    @classmethod
    def a_period(cls, days: int) -> int:
        if days not in PERIODS:
            raise ValueError(f"Choose one of {', '.join(map(str, PERIODS))} days.")
        return days


class TodayQuery(DriveScope):
    """Today's prices of the drives asked for (every drive unless narrowed as the drives list
    is). recent_days: the lowest is the cheapest of those checked within it."""

    model_config = ConfigDict(extra="forbid")
    recent_days: int = Field(
        default=7,
        ge=1,
        le=365,
        description="Only offers checked within this many days can be marked lowest.",
    )


class TrendPoint(Contract):
    """One day of a trend: the median of the drives followed, and the middle half around it."""

    days_ago: int = Field(
        description="UTC day offset from the report: 0 is today; points are oldest first."
    )
    median: int
    low: int
    high: int


class TrendSeries(Contract):
    # How many drives the points are over, of how many there are prices for in the period: only
    # those priced as the period opens are followed, so one arriving does not move the line.
    counted: int = Field(
        description="Number of drives followed: only those priced at the period opening."
    )
    of: int = Field(
        description="Number of drives with prices in the period, including later arrivals."
    )
    # Oldest first; a day with no drive to price has no point.
    points: list[TrendPoint]


class TrendPart(Contract):
    # The condition, the capacity in GB, or the store's key.
    key: str
    series: TrendSeries


class Trends(Contract):
    """Item prices over a period, in cents per terabyte. Split by store, each part is instead
    hundredths of a percent above the typical price of the drives that store shares with another."""

    days: int
    by: Literal["condition", "capacity", "store"] | None
    market: TrendSeries
    parts: list[TrendPart]
    since: datetime | None = Field(
        description="When the first price was seen, whatever the period; null when none was."
        " A period opening before it follows no drive."
    )


class PriceMark(Contract):
    """A drive in one condition, placed by the lowest item price per terabyte any store with it
    in stock asks today, in cents. lowest marks the cheapest of those checked recently."""

    drive_id: UUID
    condition: Condition
    title: str
    capacity_gb: int
    per_tb_cents: int = Field(
        description="Lowest in-stock item price per decimal TB, in US cents; shipping excluded."
    )
    lowest: bool


class StoreFreshness(Contract):
    """How fresh a store's prices are: how many offers it has, held ones and all, when the latest
    of them was checked, and when the middle one was (between the middle two, of an even
    number)."""

    store: str
    offers: int
    latest_checked_at: datetime
    median_checked_at: datetime
