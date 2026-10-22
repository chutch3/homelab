"""What becomes of a store page as collected, given what disktracker knows of it: recorded, waiting
for review, or ignored, and why. The one judgement ingestion (catalog.ingestion_service) acts on
and a preview foresees; what is known is read by them and given here."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from disktracker.catalog.rules import doubt, missing_detail


@dataclass(frozen=True)
class Seen:
    """What a page says, beyond what identifies its offer: its title, the capacity it gives, the
    other MPNs it names, and whether it is in stock (so brings a price of its own)."""

    title: str
    capacity_gb: int | None
    aliases: tuple[str, ...]
    in_stock: bool


@dataclass(frozen=True)
class Known:
    """What disktracker knows of the page's drive: the drive its MPN goes by and its capacity
    (None for none), the drive each other MPN the page names goes by (for those any does), and
    whether that drive's offer at the page's store, seller and condition has a price."""

    drive: UUID | None
    capacity: int | None
    owners: Mapping[str, UUID]
    priced: bool


@dataclass(frozen=True)
class Verdict:
    """What becomes of a page. Recorded: under the capacity to register a new drive with (None
    keeps a known drive's), with the other MPNs no drive goes by yet. Queued: for its reason,
    holding its drive's offer when the page is doubted, and naming the MPN another drive goes by
    for an alias conflict. Ignored: as a reviewer decided, or sold out with no price to carry."""

    outcome: Literal["recorded", "queued", "ignored"]
    reason: str | None = None
    hold: bool = False
    conflict: tuple[str, UUID] | None = None
    capacity: int | None = None
    fresh: tuple[str, ...] = ()


def judged(
    seen: Seen,
    identity: Mapping[str, Any] | None,
    decided: Mapping[str, Any] | None,
    known: Known,
) -> Verdict:
    """What becomes of a page whose offer is identified as a reviewer decided, if one has
    (catalog.rules.as_decided; None when it was decided to be nothing), in the order ingestion
    finds it: what identifies the offer, then doubt, then the drive's capacity, then the other
    MPNs the page names, then a price."""
    if identity is None:
        return Verdict("ignored", "decided")
    mpn = identity["mpn"]
    reason = missing_detail(mpn, identity["condition"])
    # Once a person has said what a page is, its drive's capacity stands, whatever it says.
    stated = seen.capacity_gb if decided is None else None
    # A listing a person decided is taken as decided while its page reads as it did then;
    # otherwise it is judged as it reads.
    if reason is None and (decided is None or seen.title != decided["reviewed_title"]):
        reason = doubt(seen.title, stated or known.capacity, mpn)
        if reason is not None:
            # What was recorded of its offer counts for nothing until a person settles it.
            return Verdict("queued", reason, hold=known.drive is not None)
    if reason is not None:
        return Verdict("queued", reason)
    if known.drive is None and stated is None:
        return Verdict("queued", "missing_capacity")
    if known.drive is not None and stated not in (None, known.capacity):
        return Verdict("queued", "capacity_conflict")
    # Another drive's MPNs a reviewer accepted the page naming stay that drive's, and settled.
    settled = set(decided.get("settled_aliases") or ()) if decided else set()
    fresh = []
    for alias in dict.fromkeys(seen.aliases):
        owner = known.owners.get(alias)
        if alias in settled and owner not in (None, known.drive):
            continue
        if owner is None:
            fresh.append(alias)
        elif owner != known.drive:
            # Another drive goes by it: nothing the page said is taken, and no drive merged.
            return Verdict("queued", "alias_conflict", conflict=(alias, owner))
    if not seen.in_stock and not known.priced:
        # Sold out, it carries its offer's last price on; one never priced has none to carry.
        return Verdict("ignored", "sold_out")
    return Verdict("recorded", capacity=stated, fresh=tuple(fresh))
