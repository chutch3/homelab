"""What the API returns: the published contract that clients are generated from."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from disktracker.schemas import Condition, SourceBasis, SourceKind, SourceTransport, StoreKey
from disktracker.specifications import Specifications

# Dollar amounts per TB stay strings ("11.06") so clients never round them through floats.
DecimalText = Field(pattern=r"^\d+(\.\d+)?$")


class Observation(BaseModel):
    id: UUID
    item_price_cents: int
    shipping_cents: int | None
    shipping_known: bool
    in_stock: bool
    observed_at: datetime
    entered_at: datetime
    notes: str
    acquisition_method: str
    total_cents: int
    price_per_tb: str = DecimalText


class Drive(BaseModel):
    id: UUID
    mpn: str
    aliases: list[str]
    # The maker, as a collector named it; null until one does.
    brand: str | None
    capacity_gb: int
    specifications: Specifications


class ListingSummary(BaseModel):
    """An offer with its latest price; what the listings table needs."""

    id: UUID
    title: str
    mpn: str
    store: StoreKey
    store_name: str
    seller: str
    url: str | None
    condition: Condition
    last_checked_at: datetime
    capacity_gb: int
    drive: Drive
    latest: Observation


class Listing(ListingSummary):
    """An offer with every price it has had, oldest first."""

    observations: list[Observation]


class ScrapedResult(BaseModel):
    status: Literal["recorded", "queued", "ignored"]
    listing_id: UUID | None = None
    unmatched_id: UUID | None = None


# Why a scraped offer waits in the Review queue.
UnmatchedReason = Literal[
    "missing_mpn", "missing_condition", "missing_capacity", "capacity_conflict", "missing_price"
]


class Unmatched(BaseModel):
    id: UUID
    source: str
    url: str
    title: str
    seller: str
    mpn: str | None
    condition: Condition | None
    capacity_gb: int | None
    item_price_cents: int | None
    shipping_cents: int | None
    in_stock: bool
    reason: UnmatchedReason
    first_seen_at: datetime
    last_seen_at: datetime


class ListingFacts(BaseModel):
    """What pasted listing text says of an offer; anything it does not say is null."""

    title: str | None
    mpn: str | None
    capacity_gb: int | None
    condition: Condition | None
    brand: str | None
    item_price_cents: int | None


class PreviewOffer(BaseModel):
    """One offer as the collector read it from a source being tested; nothing is kept."""

    url: str
    title: str
    mpn: str | None
    brand: str | None
    condition: str | None
    capacity_gb: int | None
    item_price_cents: int | None
    shipping_cents: int | None
    in_stock: bool
    aliases: list[str]


class PreviewVerdict(BaseModel):
    """What disktracker would do with the offer: record it, hold it for review, or ignore it."""

    outcome: Literal["recorded", "review", "ignored"]
    reason: str | None


class SourcePreview(BaseModel):
    # found: an offer was read. nothing: the store was read but no drive found. failed: the
    # store could not be read, for the reason given.
    status: Literal["found", "nothing", "failed"]
    reason: str | None
    offer: PreviewOffer | None
    verdict: PreviewVerdict | None
    # What the collector read on the way, and why a page gave no offer, in sentences.
    notes: list[str] = []


class SettingView(BaseModel):
    """One thing a kind of store needs to know: how the form asks for it, and how it is
    checked (disktracker.kinds)."""

    name: str
    label: str
    type: Literal["text", "list", "flag"]
    required: bool
    description: str
    placeholder: str
    # The group of settings it is asked for among; "" for none.
    group: str
    pattern: str
    pattern_message: str
    regex: bool
    capturing: bool
    needs: str


class SettingGroupView(BaseModel):
    name: str
    label: str
    help: str


class SourceKindView(BaseModel):
    kind: str
    label: str
    # Read by the collector; a store entered by hand is not.
    collected: bool
    # One of its pages can be read alone to test it.
    page_test: bool
    groups: list[SettingGroupView]
    settings: list[SettingView]


class StoreFact(BaseModel):
    """One thing worth knowing about a store before deciding to collect it."""

    label: str
    value: str


class InspectionCandidate(BaseModel):
    """One way of reading the store a link is from: the kind of source and its settings, why
    they were chosen, how many offers they read from the page, the first of them, and what
    disktracker would do with it."""

    kind: SourceKind
    settings: dict[str, Any]
    evidence: list[str]
    offers: int
    offer: PreviewOffer
    verdict: PreviewVerdict
    # How much there is to the store read this way, and how long a run of it would take.
    summary: list[StoreFact] = []


class SourceInspection(BaseModel):
    # found: at least one way of reading the page gave a drive. nothing: none did. failed: the
    # page could not be read, for the reason given.
    status: Literal["found", "nothing", "failed"]
    reason: str | None
    # The store the link is from, as a source's address.
    base_url: str
    candidates: list[InspectionCandidate]
    # What was looked for on the page and not found.
    notes: list[str]


class SourceView(BaseModel):
    id: UUID
    # What its prices and runs are recorded under; fixed when the source is created.
    key: str
    name: str
    kind: SourceKind
    settings: dict[str, Any]
    base_url: str
    schedule: str
    enabled: bool
    transport: SourceTransport
    basis: SourceBasis
    notes: str
    # When the schedule next falls due, in UTC; null while the source is switched off.
    next_run_at: datetime | None
