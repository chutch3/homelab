"""Pure reading of how item prices have moved across every drive: no database, no clock.

Shipping is left out, as it is from every price history. A price holds from the moment it was
recorded until the next one; an out-of-stock record means the drive could not be bought; and an
offer unchecked for longer than allowed is taken to have ended at its last check."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Literal

By = Literal["condition", "capacity", "store"]
CONDITIONS = ("new", "manufacturer_recertified", "refurbished", "used")
type Moment = tuple[int, datetime]
# A drive in one condition: what stores compete to sell.
type Item = tuple[str, str]


@dataclass(frozen=True)
class Change:
    at: datetime
    item_price_cents: int
    in_stock: bool


@dataclass(frozen=True)
class Offer:
    """One store's offer of a drive in a condition, with every change of its price, oldest first."""

    drive: str
    condition: str
    store: str
    capacity_gb: int
    last_checked_at: datetime
    changes: Sequence[Change]


def _whole(value: float) -> int:
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _quantile(values: list[float], part: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * part
    below = int(position)
    above = min(below + 1, len(ordered) - 1)
    return ordered[below] + (ordered[above] - ordered[below]) * (position - below)


def _points(sampled: list[tuple[int, list[float]]]) -> list[dict[str, int]]:
    """The median of each day's values and the middle half around it; a day with none has no point."""
    return [
        {
            "days_ago": days_ago,
            "median": _whole(_quantile(values, 0.5)),
            "low": _whole(_quantile(values, 0.25)),
            "high": _whole(_quantile(values, 0.75)),
        }
        for days_ago, values in sampled
        if values
    ]


def trends(
    offers: Sequence[Offer], now: datetime, days: int, quiet_days: int, by: By | None
) -> dict[str, Any]:
    """The typical item price per terabyte on each of the days up to now, over all drives and,
    when asked, over each part they split into. Prices are cents per terabyte; split by store, each
    store is instead hundredths of a percent above the typical price of the drives it shares."""
    moments: list[Moment] = [(ago, now - timedelta(days=ago)) for ago in range(days, -1, -1)]
    body = _read(offers, moments, now, days, quiet_days, by)
    # When the first price was seen, however long the period: so one too long for any drive to be
    # followed over can say when it will fill.
    first = min((offer.changes[0].at for offer in offers if offer.changes), default=None)
    return {**body, "since": None if first is None else first.isoformat()}


def _read(
    offers: Sequence[Offer],
    moments: Sequence[Moment],
    now: datetime,
    days: int,
    quiet_days: int,
    by: By | None,
) -> dict[str, Any]:
    """The typical price at each of the moments given, oldest first: the first is when the period
    opens, and the drives priced then are the ones followed."""

    def price(offer: Offer, moment: datetime) -> int | None:
        quiet = now - offer.last_checked_at > timedelta(days=quiet_days)
        if quiet and moment >= offer.last_checked_at:
            return None
        current = next((change for change in reversed(offer.changes) if change.at <= moment), None)
        return current.item_price_cents if current and current.in_stock else None

    def per_terabyte(item: Sequence[Offer], moment: datetime) -> float | None:
        """What a drive in one condition costs at the cheapest store, by the terabyte."""
        prices = [found for offer in item if (found := price(offer, moment)) is not None]
        return min(prices) * 1000 / item[0].capacity_gb if prices else None

    def series(chosen: Sequence[Offer]) -> dict[str, Any]:
        items: dict[Item, list[Offer]] = {}
        for offer in chosen:
            items.setdefault((offer.drive, offer.condition), []).append(offer)
        # A fixed set: only drives priced as the period opens, so one arriving never moves the line.
        followed = [
            item for item in items.values() if per_terabyte(item, moments[0][1]) is not None
        ]
        priced = [
            item
            for item in items.values()
            if any(per_terabyte(item, moment) is not None for _, moment in moments)
        ]
        sampled = [
            (ago, [found for item in followed if (found := per_terabyte(item, moment)) is not None])
            for ago, moment in moments
        ]
        return {"counted": len(followed), "of": len(priced), "points": _points(sampled)}

    def against_typical(
        own: Sequence[Offer], sold: Mapping[Item, Sequence[Offer]]
    ) -> dict[str, Any]:
        """A store's prices beside the typical price of the same drive in the same condition, on
        the drives another store sells too: stores stock different drives, so their plain averages
        do not compare. sold is every offer of each drive in each condition."""

        def rivals(mine: Offer) -> Sequence[Offer]:
            """Every offer of the same drive in the same condition, the store's own among them."""
            return sold[(mine.drive, mine.condition)]

        shared = [o for o in own if any(other.store != o.store for other in rivals(o))]
        sampled = []
        for ago, moment in moments:
            above = []
            for offer in shared:
                asked = [
                    found for other in rivals(offer) if (found := price(other, moment)) is not None
                ]
                mine = price(offer, moment)
                if mine is not None and len(asked) > 1:
                    above.append(
                        (mine / _quantile([float(cents) for cents in asked], 0.5) - 1) * 10000
                    )
            sampled.append((ago, above))
        priced = [o for o in own if any(price(o, moment) is not None for _, moment in moments)]
        return {"counted": len(shared), "of": len(priced), "points": _points(sampled)}

    parts: list[dict[str, Any]] = []
    if by == "condition":
        parts = [
            {"key": key, "series": series([o for o in offers if o.condition == key])}
            for key in CONDITIONS
            if any(offer.condition == key for offer in offers)
        ]
    elif by == "capacity":
        parts = [
            {"key": str(size), "series": series([o for o in offers if o.capacity_gb == size])}
            for size in sorted({offer.capacity_gb for offer in offers})
        ]
    elif by == "store":
        # Gathered once: looking through every offer again for each store's each offer, on each
        # day, takes minutes over a real market.
        sold: dict[Item, list[Offer]] = {}
        stocked: dict[str, list[Offer]] = {}
        for offer in offers:
            sold.setdefault((offer.drive, offer.condition), []).append(offer)
            stocked.setdefault(offer.store, []).append(offer)
        parts = [
            {"key": store, "series": against_typical(stocked[store], sold)}
            for store in sorted(stocked)
        ]
    return {"days": days, "by": by, "market": series(offers), "parts": parts}
