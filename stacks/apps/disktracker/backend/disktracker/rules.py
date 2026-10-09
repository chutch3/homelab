"""Pure decision rules for recording prices and matching scraped offers; no I/O."""

import re
from collections.abc import Iterable, Mapping
from datetime import datetime
from typing import Any

COMPARED = ("item_price_cents", "shipping_cents", "in_stock")
IDENTITY = ("store", "seller", "condition")


class CapacityRequired(Exception):
    pass


class CapacityConflict(Exception):
    pass


class PriceRequired(Exception):
    pass


def with_carried_price(values: dict[str, Any], latest: Mapping[str, Any] | None) -> dict[str, Any]:
    """A sold-out check may omit the price; it keeps the offer's last price and shipping."""
    if values["item_price_cents"] is not None:
        return values
    if latest is None:
        raise PriceRequired()
    return {
        **values,
        "item_price_cents": latest["item_price_cents"],
        "shipping_cents": latest["shipping_cents"],
    }


def unchanged(
    values: Mapping[str, Any], observed_at: datetime, latest: Mapping[str, Any] | None
) -> bool:
    """An identical price seen no earlier than the latest one only counts as a check."""
    return (
        latest is not None
        and observed_at >= latest["observed_at"]
        and all(latest[key] == values[key] for key in COMPARED)
    )


def missing_detail(mpn: str | None, condition: str | None) -> str | None:
    if mpn is None:
        return "missing_mpn"
    if condition is None:
        return "missing_condition"
    return None


def preview_verdict(offer: Mapping[str, Any], drive_capacity: int | None) -> tuple[str, str | None]:
    """What recording a scraped offer would do, and why: "recorded"; "review", when it would
    wait in the Review queue; or "ignored", when it is sold out and so has no price to record.
    drive_capacity is the capacity of the drive its MPN names, when disktracker knows it."""
    missing = missing_detail(offer["mpn"], offer["condition"])
    if missing is not None:
        return "review", missing
    if not offer["in_stock"]:
        return "ignored", "sold_out"
    if drive_capacity is None:
        return (
            ("review", "missing_capacity") if offer["capacity_gb"] is None else ("recorded", None)
        )
    if offer["capacity_gb"] not in (None, drive_capacity):
        return "review", "capacity_conflict"
    return "recorded", None


def source_key(name: str) -> str:
    """What a source's offers, prices and runs are recorded under: its name's letters and
    digits, in lower case."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def queue_reason(error: Exception) -> str:
    return {
        CapacityConflict: "capacity_conflict",
        CapacityRequired: "missing_capacity",
        PriceRequired: "missing_price",
    }[type(error)]


def new_aliases(aliases: Iterable[str], mpn: str, known: Iterable[str]) -> list[str]:
    seen = {mpn, *known}
    fresh: list[str] = []
    for alias in aliases:
        if alias not in seen:
            seen.add(alias)
            fresh.append(alias)
    return fresh


def merge_plan(
    variant_offers: Iterable[Mapping[str, Any]], drive_offers: Iterable[Mapping[str, Any]]
) -> list[tuple[Any, Any | None]]:
    """For each offer of a drive being merged away: the matching offer it combines into,
    or None when it simply moves to the surviving drive."""
    by_identity = {tuple(offer[key] for key in IDENTITY): offer["id"] for offer in drive_offers}
    return [
        (offer["id"], by_identity.get(tuple(offer[key] for key in IDENTITY)))
        for offer in variant_offers
    ]


def fill_unknown(current: Mapping[str, Any], found: Mapping[str, Any]) -> dict[str, Any]:
    """A source's specifications only fill in what nobody has entered; entered values win."""
    return {
        **current,
        **{key: value for key, value in found.items() if current.get(key) in ("unknown", [])},
    }
