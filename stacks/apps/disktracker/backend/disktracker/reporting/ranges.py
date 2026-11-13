"""Where a drive's item price has been over a period: the lowest at any of its offers in one
condition, step by step, and its range. Pure: prices in, cents out. Shipping is left out, as it
is from every price history."""

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

DAY = timedelta(days=1).total_seconds()


@dataclass(frozen=True)
class Stretch:
    """A price an offer could be bought at, from one moment to another (seconds since the
    epoch); open when it still holds now. since: when the price was first recorded."""

    offer: int
    start: float
    end: float
    price: int
    open: bool
    since: float


def half_up(value: float) -> int:
    """Rounded as the app rounds: halves up."""
    return math.floor(value + 0.5)


def stretches(
    offer: int, prices: Sequence[dict[str, Any]], last_checked: datetime, now: float, quiet: float
) -> list[Stretch]:
    """Each price holds until the next one recorded, an out-of-stock record ends it, and an offer
    unchecked for longer than quiet seconds is taken to have ended at its last check."""
    checked = last_checked.timestamp()
    end = checked if now - checked > quiet else now
    ordered = sorted(
        prices, key=lambda price: (price["observed_at"], price["entered_at"], str(price["id"]))
    )
    found = []
    for index, price in enumerate(ordered):
        start = price["observed_at"].timestamp()
        last = index + 1 == len(ordered)
        until = min(end, end if last else ordered[index + 1]["observed_at"].timestamp())
        if price["in_stock"] and until >= start:
            found.append(
                Stretch(offer, start, until, price["item_price_cents"], last and end == now, start)
            )
    return found


Offers = Sequence[tuple[Sequence[dict[str, Any]], datetime]]


@dataclass(frozen=True)
class Step:
    """The lowest price at any offer, from one moment to another (seconds since the epoch)."""

    start: float
    end: float
    price: int


def lowest_steps(
    offers: Offers, now: datetime, days: int, quiet_days: int
) -> tuple[list[Step], list[int]]:
    """The lowest item price at any of these offers (each its prices and when it was last
    checked) over the days up to now, step by step with gaps where none had it in stock, ending
    on today's price; and what each offer on sale now costs. The chart of a drive draws the same
    steps: shared examples hold the two to one answer."""
    end = now.timestamp()
    start = end - days * DAY
    held = [
        Stretch(s.offer, max(s.start, start), s.end, s.price, s.open, s.since)
        for index, (prices, checked) in enumerate(offers)
        for s in stretches(index, prices, checked, end, quiet_days * DAY)
    ]
    held = [s for s in held if s.end > s.start or s.open]
    moments = sorted({moment for s in held for moment in (s.start, s.end)})
    lowest: list[Step] = []
    for index, moment in enumerate(moments[:-1]):
        on_sale = [s for s in held if s.start <= moment < s.end]
        if not on_sale:
            continue
        winner = min(on_sale, key=lambda s: s.price)
        if lowest and lowest[-1].end == moment and lowest[-1].price == winner.price:
            lowest[-1] = Step(lowest[-1].start, moments[index + 1], winner.price)
        else:
            lowest.append(Step(moment, moments[index + 1], winner.price))
    # The lowest ends on today's price: where the last step is not it, a step of no length is.
    current = min((s for s in held if s.open), key=lambda s: s.price, default=None)
    if current and (not lowest or lowest[-1].end != end or lowest[-1].price != current.price):
        lowest.append(Step(end, end, current.price))
    return lowest, [s.price for s in held if s.open]


def price_range(
    offers: Offers, now: datetime, days: int, quiet_days: int
) -> dict[str, int | None] | None:
    """The range of the lowest item price at any of these offers over the days up to now: today's
    (None when none is in stock), the lowest and highest, the average weighed by how long each
    held, and how many days of prices there are. None when none was in stock in the period."""
    lowest, today = lowest_steps(offers, now, days, quiet_days)
    if not lowest:
        return None
    prices = [step.price for step in lowest]
    covered = sum(step.end - step.start for step in lowest)
    return {
        "today": min(today) if today else None,
        "low": min(prices),
        "high": max(prices),
        # A price that has held for no time yet is its own average.
        "average": half_up(sum(step.price * (step.end - step.start) for step in lowest) / covered)
        if covered
        else prices[0],
        "days": half_up((now.timestamp() - lowest[0].start) / DAY),
    }
