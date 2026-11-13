"""Pure decision rules for recording prices and matching scraped offers; no I/O. Capacities are
whole decimal gigabytes (1 TB = 1000 GB), as drives and cards are sold; amounts are integer USD
cents."""

import re
from collections.abc import Mapping
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from listing_facts.readers import capacity_in

from disktracker.errors import (
    DecisionConflict,
    IdempotencyConflict,
    MergeConflict,
    PriceRequired,
)

COMPARED = ("item_price_cents", "shipping_cents", "in_stock")


def normalize_mpn(raw: str) -> str:
    """One canonical spelling per MPN, so case and stray spacing never split a drive."""
    return re.sub(r"\s+", "", raw).upper()


def capacity_label(gigabytes: int) -> str:
    if gigabytes < 1000:
        return f"{gigabytes} GB"
    return f"{format((Decimal(gigabytes) / 1000).normalize(), 'f')} TB"


def comparable_price(item: int, shipping: int | None, capacity_gb: int) -> tuple[int, str]:
    """Unknown shipping (None) counts as zero; callers flag it separately."""
    total = item + (shipping or 0)
    # cents / 100 = dollars; gigabytes / 1000 = terabytes.
    per_tb = (Decimal(total) * 10 / capacity_gb).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return total, str(per_tb)


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


# More than any drive holds: the largest sold hold 245.76 TB.
MOST_A_DRIVE_HOLDS_GB = 256_000

# A title saying it is not one disk drive: several sold together, something that holds drives,
# tape, or network equipment.
NOT_ONE_DRIVE_PATTERNS = (
    # 25x1.8TB, w/25x1.2TB: a count is written tight, with a small x, so a model name
    # ending in X (Pro-5X 3TB) is not one, and two actuators (2x 9TB) are one drive.
    r"\b(?:[3-9]|\d{2,})(?-i:x)\d+(?:\.\d+)?\s?(?:TB|GB)\b",
    r"\(\s?\d+\s?x\s?\d+(?:\.\d+)?\s?\)",
    r"\b\d+(?:\.\d+)?\s?(?:TB|GB)\s?x\s?\d+\b",
    r"\b\d+[- ]pack\b",
    r"\bpack of \d+",
    r"\blot of \d+",
    r"\bbundle\b",
    r"\bjbod\b",
    r"\b(?:dual|\d)[- ]bay\b",
    r"\benclosure\b",
    r"\bstorage array\b",
    r"\blto[- ]?\d\b",
    r"\btape\b",
    r"\bauto ?loader\b",
    r"\bultrium\b",
    # Two ports are a drive's; many are a switch's.
    r"\bqsfp",
    r"\bswitch\b",
    r"\b\d{2,} ports\b",
)
NOT_ONE_DRIVE = re.compile("|".join(NOT_ONE_DRIVE_PATTERNS), re.IGNORECASE)


def doubt(title: str | None, capacity_gb: int | None, mpn: str | None = None) -> str | None:
    """Why a collected offer cannot be taken as one drive of the capacity it says, for a person
    to settle: "not_a_single_drive"; or "implausible_capacity", for more than any drive holds or
    other than its own title says, read past its part number (one misread from a part number
    run into its capacity); None when nothing is doubted."""
    # Not one drive first: what the title of several says is all of them together.
    if title and NOT_ONE_DRIVE.search(title):
        return "not_a_single_drive"
    if capacity_gb is None:
        return None
    if capacity_gb > MOST_A_DRIVE_HOLDS_GB:
        return "implausible_capacity"
    if title and mpn and capacity_in(title, mpn) not in (None, capacity_gb):
        return "implausible_capacity"
    return None


def fill_unknown(current: Mapping[str, Any], found: Mapping[str, Any]) -> dict[str, Any]:
    """A source's specifications only fill in what nobody has entered; entered values win."""
    return {
        **current,
        **{key: value for key, value in found.items() if current.get(key) in ("unknown", [])},
    }


LEGACY_RECEIPT = (
    "This save key was used before prices were recorded this way, so this request cannot be"
    " matched to the one it answered. Nothing was saved: check whether the price is already"
    " recorded, then save it under a new key."
)


def replayed(result: Mapping[str, Any] | None, kept: str, fingerprint: str) -> dict[str, Any]:
    """The answer a save key was given, for a request sent again under it. A key kept before
    prices were unified holds a whole offer under a fingerprint made another way: it cannot be
    shown to answer this request, so it is neither replayed nor written again. A key used for a
    different request is refused."""
    if "status" not in (result or {}):
        raise IdempotencyConflict(LEGACY_RECEIPT)
    if kept != fingerprint:
        raise IdempotencyConflict("This save key was already used for a different request.")
    return dict(result or {})


def decided_again(
    earlier: Mapping[str, Any], result: Mapping[str, Any] | None, decision: Mapping[str, Any]
) -> dict[str, Any]:
    """The answer a review decision was given, for the same decision sent again; a different
    decision is refused."""
    if earlier != decision:
        raise DecisionConflict("This review item was already decided differently.")
    return dict(result or {})


def as_decided(
    identity: dict[str, Any], decided: Mapping[str, Any] | None
) -> dict[str, Any] | None:
    """What identifies a collected offer once what a reviewer decided of its listing is applied:
    the MPN and condition the reviewer gave, whatever the page says. None when the listing was
    decided to be nothing to track."""
    if decided is None:
        return identity
    if decided["ignored"]:
        return None
    return {**identity, "mpn": decided["mpn"], "condition": decided["condition"]}


def queued_fields(
    entry: Mapping[str, Any], identity: Mapping[str, Any], price: Mapping[str, Any], reason: str
) -> dict[str, Any]:
    """What is kept of an offer waiting for review: what its page said, as it said it (its title,
    seller, capacity, the MPN and condition it gave, and what it said of the drive) and who
    submitted it, its price, its store and why it waits."""
    return {
        **{key: entry[key] for key in ("aliases", "brand", "specifications")},
        **{key: entry[key] for key in ("title", "seller", "capacity_gb", "provenance")},
        **{key: price[key] for key in ("item_price_cents", "shipping_cents", "in_stock")},
        "store": identity["store"],
        "mpn": entry["mpn"],
        "condition": entry["condition"],
        "url": str(entry["url"]),
        "reason": reason,
    }


UNKNOWN = "unknown"
SCALAR_SPECIFICATIONS = ("media_type", "form_factor", "interface", "recording_type")


def merged_drive(target: Mapping[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    """What two drives merged into one are: the target's capacity, brand and specifications, with
    what it lacks filled in from the source. A brand the target has stands, whatever the source
    names. A capacity or a known specification both have and differ on is refused, every one of
    them at once; intended uses are alike in any order."""
    conflicts: list[str] = []
    if target["capacity_gb"] != source["capacity_gb"]:
        conflicts.append("capacity_gb")
    specifications = dict(target["specifications"])
    for key in SCALAR_SPECIFICATIONS:
        had, given = specifications.get(key, UNKNOWN), source["specifications"].get(key, UNKNOWN)
        if had == UNKNOWN:
            specifications[key] = given
        elif given not in (UNKNOWN, had):
            conflicts.append(f"specifications.{key}")
    uses, given_uses = (
        specifications.get("intended_use", []),
        source["specifications"].get("intended_use", []),
    )
    if not uses:
        specifications["intended_use"] = given_uses
    elif given_uses and set(given_uses) != set(uses):
        conflicts.append("specifications.intended_use")
    if conflicts:
        raise MergeConflict(conflicts)
    return {
        "capacity_gb": target["capacity_gb"],
        "brand": target["brand"] or source["brand"],
        "specifications": specifications,
    }


def combined_offer(survivor: Mapping[str, Any], absorbed: Mapping[str, Any]) -> dict[str, Any]:
    """What an offer combined with another of the same store, seller and condition is: held if
    either was (with the survivor's reason if it was held), and last checked when either was.
    A merge never releases a hold."""
    checked = [at for at in (survivor["last_checked_at"], absorbed["last_checked_at"]) if at]
    return {
        "held_reason": survivor["held_reason"] or absorbed["held_reason"],
        "last_checked_at": max(checked) if checked else None,
    }
