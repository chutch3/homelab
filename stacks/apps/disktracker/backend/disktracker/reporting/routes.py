"""Reporting over HTTP: what the recorded prices add up to."""

from typing import Annotated, Any

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query

from disktracker.container import Container
from disktracker.reporting.schemas import PriceMark, TodayQuery, TrendQuery, Trends
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
