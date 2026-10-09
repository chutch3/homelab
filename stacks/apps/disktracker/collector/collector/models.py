"""What a source hands to disktracker: one offer as scraped, possibly incomplete."""

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, NamedTuple
from uuid import UUID

from listing_text.readers import ConditionRules, Specifications

from disktracker_api.models import ListingSummary

# disktracker accepts titles up to this many characters.
TITLE_LIMIT = 160
FREE_SHIPPING = 0


@dataclass(frozen=True)
class Store:
    """Where a source reads: its key, which its offers, prices and runs are recorded under, its
    address, the least time between two requests to it, and the condition rules its offers are
    read with this round."""

    key: str
    base_url: str
    min_delay: float = 0
    conditions: ConditionRules = ()


@dataclass(frozen=True)
class ScrapedOffer:
    # The key of the source it was read from, which is the store it is recorded under.
    source: str
    url: str
    title: str
    mpn: str | None
    condition: str | None
    capacity_gb: int | None
    item_price_cents: int | None
    in_stock: bool
    seller: str = ""
    shipping_cents: int | None = None
    aliases: tuple[str, ...] = ()
    # Normalized drive specifications the source states.
    specifications: Specifications | None = None
    # The drive's maker, as named by titles.maker_named.
    brand: str | None = None

    @classmethod
    def recheck(
        cls,
        listing: ListingSummary,
        *,
        source: str,
        item_price_cents: int | None,
        in_stock: bool,
        shipping_cents: int | None,
    ) -> "ScrapedOffer":
        """Re-post an offer disktracker already knows, under the identity it has for it, with
        what its product page says now."""
        return cls(
            source=source,
            url=listing.url or "",
            title=listing.title,
            mpn=listing.mpn,
            condition=listing.condition,
            capacity_gb=listing.drive.capacity_gb,
            item_price_cents=item_price_cents,
            in_stock=in_stock,
            shipping_cents=shipping_cents,
        )

    def fields(self) -> dict[str, Any]:
        """The offer as plain data."""
        return {**asdict(self), "aliases": list(self.aliases)}

    def payload(self, observed_at: datetime) -> dict[str, Any]:
        return {**self.fields(), "observed_at": observed_at.isoformat()}


@dataclass(frozen=True)
class RunSummary:
    """How one run went. The post counts are for the offers the store listed; rechecks of
    offers it no longer lists are counted apart."""

    source: str
    completed: bool
    seen: int = 0
    recorded: int = 0
    queued: int = 0
    ignored: int = 0
    failed: int = 0
    rechecked: int = 0
    recheck_failed: int = 0
    # The run ended early because disktracker asked it to stop, rather than failing.
    stopped: bool = False


class Posted(NamedTuple):
    """What disktracker did with a posted offer, and the listing it recorded it on."""

    status: str
    listing_id: UUID | None = None
