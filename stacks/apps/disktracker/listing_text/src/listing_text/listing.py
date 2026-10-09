"""Reading an offer from text a person copied off a listing page: its title and price, and
what the readers find in it."""

import re
from decimal import Decimal
from typing import NamedTuple

from listing_text.readers import (
    ConditionRules,
    capacity_in,
    condition_in,
    maker_named,
    mpn_from_title,
)

# disktracker keeps titles up to this many characters.
TITLE_LIMIT = 160
AMOUNT = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d{1,2})?")
# An amount right after one of these is a former, list or saved price, not what the offer costs.
NOT_THE_PRICE = re.compile(
    r"\b(?:was|list(?:\s+price)?|msrp|reg(?:ular)?\.?(?:\s+price)?|save)\s*:?\s*$", re.IGNORECASE
)


class ListingFacts(NamedTuple):
    title: str | None
    mpn: str | None
    capacity_gb: int | None
    condition: str | None
    brand: str | None
    item_price_cents: int | None


def price_in(text: str) -> int | None:
    """The first dollar amount, in cents, that is not a former, list or saved price."""
    for match in AMOUNT.finditer(text):
        line_before = text[: match.start()].rsplit("\n", 1)[-1]
        if not NOT_THE_PRICE.search(line_before):
            return int(Decimal(match[1].replace(",", "") + (match[2] or "")) * 100)
    return None


def read_listing(text: str, conditions: ConditionRules) -> ListingFacts:
    """The first line is the title; the readers look through all of the text."""
    title = next((line.strip() for line in text.splitlines() if line.strip()), None)
    return ListingFacts(
        title=title[:TITLE_LIMIT] if title else None,
        mpn=mpn_from_title(text),
        capacity_gb=capacity_in(text),
        condition=condition_in(conditions, text),
        brand=maker_named(text),
        item_price_cents=price_in(text),
    )
