"""Reporting's public contract: what its routes return."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import ConfigDict, Field, field_validator

from disktracker.catalog.schemas import (
    Condition,
    Drive,
    DriveScope,
    OfferSummary,
    PriceRange,
    RangeQuery,
)
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


Sort = Literal[
    "unit-asc", "unit-desc", "total-asc", "total-desc",
    "capacity-asc", "capacity-desc", "checked-desc", "checked-asc",
]  # fmt: skip


class MarketQuery(RangeQuery, DriveScope):
    """Which drives of the market to list, in what order, and which part of the list. Filters
    apply to offers: a drive is listed when any offer of it matches, and is shown by the cheapest
    of those in stock. drive_id: only this drive, if it matches (whether the filters hide it)."""

    model_config = ConfigDict(extra="forbid")
    drive_id: UUID | None = Field(default=None, description="Only this drive, if it matches")
    max_total_cents: int | None = Field(
        default=None, ge=0, description="Maximum item price plus known shipping, in US cents."
    )
    in_stock: bool = Field(default=True, description="Only offers in stock; false for all")
    recent_only: bool = Field(default=False, description="Only offers checked recently")
    sort: Sort = Field(
        default="unit-asc",
        description="unit sorts by total dollars per TB; total includes known shipping; checked sorts by last check time.",
    )
    limit: int = Field(default=50, ge=1, le=500, description="Maximum drives in this page.")
    offset: int = Field(default=0, ge=0, description="Number of matching items to skip.")


class ConditionPrices(Contract):
    """A condition a drive is offered in among the offers that match: how many offers, how many
    of them in stock, and the lowest total of those (null when none is)."""

    condition: Condition
    offers: int
    in_stock: int
    lowest_total_cents: int | None


class MarketRow(Contract):
    """A drive as the market shows it: by its cheapest matching offer in stock (else its cheapest
    matching offer), with how many stores and sellers offer it and what each condition it is
    offered in costs, among the offers that match, and the range of its price in the condition of
    the offer it is shown by."""

    drive: Drive
    offer: OfferSummary
    stores: int
    conditions: list[ConditionPrices]
    range: PriceRange | None


class Choice[T](Contract):
    value: T
    drives: int


class FilterOptions(Contract):
    """What the filters can choose from: every option the catalogue has, each with how many drives
    choosing it would give, with the search and every other filter as asked but not its own
    group's, whichever page is shown."""

    brands: list[Choice[str]]
    capacities: list[Choice[int]]
    conditions: list[Choice[Condition]]


class Lowest(Contract):
    """The offers with the lowest total and the lowest total per terabyte among every offer that
    matches, in stock and checked recently."""

    total: list[UUID]
    unit: list[UUID]


class Market(Contract):
    """A part of the market. total: drives that match; offers: offers that match; sold_out: drives
    left out only because no store has them in stock; catalogued: drives with an offer that
    counts, whatever the filters. as_of: the moment recency and ranges are judged against."""

    items: list[MarketRow]
    total: int
    offers: int
    sold_out: int
    limit: int
    offset: int
    catalogued: int
    as_of: datetime
    lowest: Lowest
    filter_options: FilterOptions
