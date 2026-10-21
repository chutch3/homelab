"""Reporting over HTTP: what the recorded prices add up to."""

from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from disktracker.catalog.schemas import Condition
from disktracker.container import Container
from disktracker.reporting.schemas import (
    Market,
    MarketQuery,
    PriceMark,
    PriceRange,
    PriceRangeQuery,
    StoreFreshness,
    TodayQuery,
    TrendQuery,
    Trends,
)
from disktracker.reporting.service import ReportingService

router = APIRouter(prefix="/api")


Reporting = Annotated[ReportingService, Depends(Provide[Container.reporting_service])]


@router.get("/trends", response_model=Trends, tags=["Reports"], summary="Read market price trends")
@inject
def price_trends(reporting: Reporting, query: Annotated[TrendQuery, Query()]) -> dict[str, Any]:
    """The typical item price per terabyte on each day of a period, over the drives asked for
    (every drive, or narrowed by the same filters as the drives list) and over each condition,
    capacity or store when asked. recent_days: an offer unchecked for longer
    is taken to have ended at its last check. Only drives priced at the opening of the period
    are followed, so new arrivals do not move the historical line. A day with no available
    prices has no point. Item prices exclude shipping. Market values are cents per decimal TB;
    when split by store, part values are hundredths of a percent above the typical price of
    shared drives. Results are recalculated when relevant data changes or a new UTC day begins.
    """
    return reporting.trends(query.days, query.by, query.recent_days, query.scope())


@router.get(
    "/reports/market", response_model=Market, tags=["Reports"], summary="Read the market for drives"
)
@inject
def market(reporting: Reporting, query: Annotated[MarketQuery, Query()]) -> dict[str, Any]:
    """The drives that match, a page at a time, each shown by its cheapest matching offer in
    stock, with how many stores and sellers offer it and what each condition it is offered in
    costs among the matches, and the range of its price; with the lowest prices among every
    match, the filter options of every drive, and how many drives there are to buy at all.

    Repeat a parameter for several choices, e.g. `brand=Seagate&brand=Toshiba`. Choices within
    a filter use OR; different filters use AND. Filters match offers, then group them by drive.
    Each filter option counts the drives choosing it would give, with every other filter as
    asked. total counts matching drives before pagination; offers counts matching offers. Only
    offers that count (none held for review) are in the market. drive_id: whether one drive is
    among the matches.
    """
    return reporting.market(query)


@router.get(
    "/reports/price-ranges",
    response_model=dict[Condition, PriceRange | None],
    tags=["Reports"],
    summary="Read a drive's price range in each condition",
)
@inject
def price_ranges(
    reporting: Reporting, query: Annotated[PriceRangeQuery, Query()]
) -> dict[str, Any]:
    """Where a drive's lowest item price in each condition it is offered in has been over
    range_days (30, 90 or 180), from the offers that count (none held for review): null in a
    condition no offer of it was in stock in then. An offer unchecked for longer than
    recent_days is taken to have ended at its last check. A drive with no such offer, or none at
    all, has no range in any condition."""
    return reporting.price_ranges(query)


@router.get(
    "/reports/prices-today",
    response_model=list[PriceMark],
    tags=["Reports"],
    summary="Read current prices per terabyte",
)
@inject
def prices_today(
    reporting: Reporting, query: Annotated[TodayQuery, Query()]
) -> list[dict[str, Any]]:
    """What each drive asked for (every drive, or narrowed by the same filters as the drives
    list) costs today in each condition it is in stock in, by item price per terabyte, cheapest
    first. recent_days: the lowest is the cheapest of those checked within it."""
    return reporting.prices_today(query.recent_days, query.scope())


@router.get(
    "/reports/store-freshness",
    response_model=list[StoreFreshness],
    tags=["Reports"],
    summary="Read how fresh each store's prices are",
)
@inject
def store_freshness(reporting: Reporting) -> list[dict[str, Any]]:
    """Each store with offers, by key: how many offers it has, held for review or not, when the
    latest of them was checked, and when the middle one was (between the middle two, of an even
    number)."""
    return reporting.store_freshness()
