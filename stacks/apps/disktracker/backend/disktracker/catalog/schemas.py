"""The catalog's public contract: what its routes accept and what they return. Clients are
generated from these; database and domain code do not depend on FastAPI."""

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import (
    AfterValidator,
    AwareDatetime,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic.json_schema import SkipJsonSchema

from disktracker.catalog.rules import normalize_mpn
from disktracker.contract import Contract

# A drive's specifications, as plain entered values.
MediaType = Literal["hdd", "ssd", "flash_card", "unknown"]
FormFactor = Literal["3_5", "2_5", "m_2", "microsd", "sd", "unknown"]
Interface = Literal["sata", "sas", "nvme_pcie", "usb", "unknown"]
Recording = Literal["cmr", "smr", "unknown"]
IntendedUse = Literal["nas", "surveillance", "enterprise", "desktop", "archive"]


class Specifications(Contract):
    model_config = ConfigDict(extra="forbid")
    media_type: MediaType = "unknown"
    form_factor: FormFactor = "unknown"
    interface: Interface = "unknown"
    recording_type: Recording = "unknown"
    intended_use: list[IntendedUse] = []

    @field_validator("intended_use")
    @classmethod
    def once_each(cls, value: list[IntendedUse]) -> list[IntendedUse]:
        return list(dict.fromkeys(value))


Cents = Annotated[int, Field(strict=True, ge=0, le=1_000_000_000)]


# Whole decimal gigabytes (1 TB = 1000 GB), up to 10 PB.
Capacity = Annotated[
    int,
    Field(strict=True, gt=0, le=10_000_000, description="Capacity in decimal GB; 1 TB = 1,000 GB."),
]


NormalizedMpn = Annotated[str, AfterValidator(normalize_mpn), Field(min_length=1, max_length=100)]


Condition = Literal["new", "manufacturer_recertified", "refurbished", "used"]


# A store's key: the key of the source offers are recorded under; Other (named by seller) is
# for one-off stores.
StoreKey = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[a-z0-9]+$")]


class ObservationInput(Contract):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    in_stock: bool = True
    item_price_cents: Cents | None = Field(
        default=None,
        validate_default=True,
        description="Positive item price in US cents, excluding shipping. Required when in stock; when out of stock, omission reuses the previous price.",
    )
    shipping_cents: Cents | None = Field(
        default=0,
        description="Shipping in US cents: 0 means free, null means unknown. Unknown shipping contributes zero to totals.",
    )
    notes: str = Field(default="", max_length=2000)
    observed_at: AwareDatetime | None = Field(
        default=None,
        description="When the price was observed, with a timezone offset. Omit to use server time; backdated prices are accepted.",
    )

    @field_validator("item_price_cents")
    @classmethod
    def priced_when_in_stock(cls, value: int | None, info: ValidationInfo) -> int | None:
        if value is None and info.data.get("in_stock", True):
            raise ValueError("Enter the item price.")
        # A store writes 0 for what it sells only by quote; nothing is sold for nothing.
        if value == 0:
            raise ValueError("Enter a price above zero.")
        return value


# Who submitted a price: a person, or a collector. Where it was seen is the offer's store.
Provenance = Literal["manual", "collected"]


class PriceInput(ObservationInput):
    """One observed price of an offer whose drive is already known, from a person or a collector
    rechecking it. The offer is named (offer_id), or its drive is (drive_id), with the store,
    seller and condition it is offered in: an offer new to them is made, titled and addressed by
    title and url when given. Nothing here says what a drive is: a drive is made or corrected
    beforehand, and a store page described is taken in at /ingestions."""

    offer_id: UUID | None = Field(
        default=None,
        description="Existing offer UUID; when supplied, omit drive_id, store, condition, title and URL.",
    )
    drive_id: UUID | None = Field(
        default=None,
        validate_default=True,
        description="Existing drive UUID, for an offer named by its store, seller and condition.",
    )
    provenance: Provenance = Field(
        default="manual",
        description="Who submitted the price. A collector submits here only a recheck of an offer it names.",
    )
    store: StoreKey | None = Field(
        default=None,
        validate_default=True,
        description="Source key from GET /api/sources, not its UUID. Required with drive_id; other requires seller.",
    )
    seller: str = Field(default="", max_length=120)
    condition: Condition | None = Field(default=None, validate_default=True)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    url: HttpUrl | None = None

    @field_validator("drive_id")
    @classmethod
    def offer_or_drive(cls, drive_id: UUID | None, info: ValidationInfo) -> UUID | None:
        named = info.data.get("offer_id") is not None
        if named and drive_id is not None:
            raise ValueError("Name the offer or its drive, not both.")
        if not named and drive_id is None:
            raise ValueError("Name the offer, or the drive it is of.")
        return drive_id

    @field_validator("provenance")
    @classmethod
    def collected_pages_are_ingested(cls, provenance: str, info: ValidationInfo) -> str:
        if provenance == "collected" and info.data.get("offer_id") is None:
            raise ValueError(
                "Send a collected page of an offer not named by id to /api/ingestions."
            )
        return provenance

    @field_validator("store")
    @classmethod
    def named_or_placed(cls, store: str | None, info: ValidationInfo) -> str | None:
        named = info.data.get("offer_id") is not None
        if named and store is not None:
            raise ValueError("Leave the store out when the offer is named.")
        if info.data.get("drive_id") is not None and store is None:
            raise ValueError("Choose a store.")
        return store

    @field_validator("seller")
    @classmethod
    def other_stores_need_a_seller(cls, seller: str, info: ValidationInfo) -> str:
        if info.data.get("store") == "other" and not seller:
            raise ValueError("Name the seller when the store is Other.")
        return seller

    @field_validator("condition")
    @classmethod
    def a_condition_unless_named(cls, condition: str | None, info: ValidationInfo) -> str | None:
        named = info.data.get("offer_id") is not None
        if named and condition is not None:
            raise ValueError("Leave this out when the offer is named.")
        if info.data.get("drive_id") is not None and condition is None:
            raise ValueError("Choose its condition.")
        return condition


class IngestionInput(ObservationInput):
    """One observation of a store page as a collector read it: the offer described, never named,
    by its store, the MPN and condition the page gives (either may be missing) and, for a one-off
    store, its seller. One that cannot be matched to a drive waits for review, which shows the
    reviewer its page and title."""

    store: StoreKey = Field(description="Source key from GET /api/sources; other requires seller.")
    seller: str = Field(default="", max_length=120)
    mpn: NormalizedMpn | None = None
    condition: Condition | None = None
    title: str = Field(min_length=1, max_length=160)
    url: HttpUrl
    capacity_gb: Capacity | None = None
    # What the page says of the drive. Other MPNs it goes by are declared for it; the
    # specifications and brand fill in only what nobody has entered.
    aliases: list[NormalizedMpn] = []
    specifications: Specifications | None = None
    brand: str | None = Field(default=None, min_length=1, max_length=60)

    @field_validator("seller")
    @classmethod
    def other_stores_need_a_seller(cls, seller: str, info: ValidationInfo) -> str:
        if info.data.get("store") == "other" and not seller:
            raise ValueError("Name the seller when the store is Other.")
        return seller


class MatchDecision(Contract):
    """A reviewer's decision that a queued offer is this drive (one already recorded) in this
    condition: its price is recorded, and later prices of it are matched the same way. It never
    says what the drive is: a drive is made (POST /drives) or corrected (PATCH /drives/{id})
    beforehand."""

    model_config = ConfigDict(extra="forbid")
    decision: Literal["match"]
    drive_id: UUID
    condition: Condition


class IgnoreDecision(Contract):
    """A reviewer's decision that a queued offer is nothing to track: later prices of it are
    ignored."""

    model_config = ConfigDict(extra="forbid")
    decision: Literal["ignore"]


ReviewDecision = Annotated[MatchDecision | IgnoreDecision, Field(discriminator="decision")]


class DecisionResult(Contract):
    """What a review decision did: matched names the offer its price was recorded for; ignored
    names none."""

    status: Literal["matched", "ignored"]
    offer_id: UUID | None


class OfferEdit(Contract):
    """Details that can change in place; MPN, store, seller and condition identify the offer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    url: HttpUrl | None = None


class DriveInput(Contract):
    """A drive made on its own, before any price of it: its MPN, which no drive may go by already,
    its capacity, and what is known of it. Specifications left out are unknown."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    mpn: NormalizedMpn
    capacity_gb: Capacity
    brand: str | None = Field(default=None, max_length=60)
    specifications: Specifications = Field(default_factory=Specifications)

    @field_validator("brand")
    @classmethod
    def blank_is_unknown(cls, brand: str | None) -> str | None:
        return brand or None


class MergeInput(Contract):
    """The drive another is merged into: it survives."""

    model_config = ConfigDict(extra="forbid")
    target_drive_id: UUID


class CombinedOffer(Contract):
    """An offer of the absorbed drive combined into the surviving drive's offer of the same
    store, seller and condition: its prices are that offer's now."""

    absorbed_offer_id: UUID
    offer_id: UUID


class MergeResult(Contract):
    status: Literal["merged"]
    drive_id: UUID
    absorbed_drive_id: UUID
    combined_offers: list[CombinedOffer]


class AliasInput(Contract):
    model_config = ConfigDict(extra="forbid")
    mpn: NormalizedMpn


class SpecificationsEdit(Contract):
    """Specifications corrected by hand: each one given takes the place of the one kept, and
    each one left out stays. None can be cleared; unknown is a value like any other."""

    model_config = ConfigDict(extra="forbid")
    media_type: MediaType = "unknown"
    form_factor: FormFactor = "unknown"
    interface: Interface = "unknown"
    recording_type: Recording = "unknown"
    intended_use: list[IntendedUse] = []


class DriveEdit(Contract):
    """A drive corrected by hand: what is given changes, and what is left out stays. Capacity and
    specifications cannot be cleared; a null or blank brand makes it unknown again, until a source
    names it. Its MPNs change only by declaring an alias."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    capacity_gb: Capacity | SkipJsonSchema[None] = None
    specifications: SpecificationsEdit | SkipJsonSchema[None] = None
    brand: str | None = Field(default=None, max_length=60)

    @field_validator("capacity_gb", "specifications")
    @classmethod
    def kept(cls, value: object) -> object:
        # Run only on what a request gives: left out, these stay as they are.
        if value is None:
            raise ValueError("A drive always has this; it can be corrected but not cleared.")
        return value

    @field_validator("brand")
    @classmethod
    def blank_is_unknown(cls, brand: str | None) -> str | None:
        return brand or None


class ListingText(Contract):
    """Text a person copied from a listing page."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=5000, pattern=r"\S")


def a_regular_expression(pattern: str) -> str:
    try:
        re.compile(pattern)
    except re.error as error:
        raise ValueError(f"Enter a regular expression ({error}).") from error
    return pattern


class ConditionRule(Contract):
    """Text matching the pattern (a case-insensitive regular expression) names the condition;
    rules are read in order and the first match wins."""

    model_config = ConfigDict(extra="forbid")
    pattern: Annotated[
        str, Field(min_length=1, max_length=200), AfterValidator(a_regular_expression)
    ]
    condition: Condition


# What the routes return.


class Observation(Contract):
    id: UUID
    item_price_cents: int
    shipping_cents: int | None
    shipping_known: bool
    in_stock: bool
    observed_at: datetime
    entered_at: datetime
    notes: str
    provenance: Provenance
    total_cents: int
    price_per_tb: str = Field(
        pattern=r"^\d+(\.\d+)?$",
        description="Total including known shipping per decimal TB, as a dollar string; e.g. 11.06.",
    )


class Drive(Contract):
    id: UUID
    mpn: str
    aliases: list[str]
    # The maker, as a collector named it; null until one does.
    brand: str | None
    capacity_gb: int
    specifications: Specifications


# Why a collected offer cannot be taken as one drive of the capacity it says.
# not_a_single_drive: its title says it is several drives, something holding drives, tape or
# network equipment. implausible_capacity: it says it holds more than any drive does.
Doubt = Literal["not_a_single_drive", "implausible_capacity"]


class OfferSummary(Contract):
    """An offer with its latest price; what a table of offers needs."""

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
    doubt: Doubt | None = Field(
        description="Why it is held while a person settles what its page is: it may not be one"
        " drive of its drive's capacity. Held, it counts in no ranking, no prices today and no"
        " trend; null when it is not held."
    )


class Offer(OfferSummary):
    """An offer with every price it has had, oldest first."""

    observations: list[Observation]


class PriceResult(Contract):
    """What was done with a submitted price.

    recorded: offer_id is the offer it is for, and price_id the price made, or null when the
    price was the same as the offer's last and so only counted as a check of it.
    queued: the offer could not be matched and waits for review as review_item_id.
    ignored: nothing was kept, as an earlier review decided, or as it was sold out and never
    seen in stock. Whatever is not named for a status is null."""

    status: Literal["recorded", "queued", "ignored"]
    offer_id: UUID | None = None
    price_id: UUID | None = None
    review_item_id: UUID | None = None


# Why a scraped offer waits in the Review queue.
ReviewReason = Literal[
    "missing_mpn",
    "missing_condition",
    "missing_capacity",
    "capacity_conflict",
    "missing_price",
    "alias_conflict",
    Doubt,
]


class ReviewItem(Contract):
    """A listing waiting for a reviewer to say what it is: what its page said, as it said it.
    Several offers of one page each wait as their own."""

    id: UUID
    store: str
    url: str
    title: str
    seller: str
    mpn: str | None = Field(description="The MPN as the page gave it; null where it gave none.")
    condition: Condition | None = Field(description="As the page gave it; null where it gave none.")
    capacity_gb: int | None
    aliases: list[str] | None = Field(
        description="Other MPNs the page gave; null where they were not kept (queued before now)."
    )
    brand: str | None
    specifications: Specifications | None = Field(
        description="What the page said of the drive; null where nothing was kept."
    )
    conflict_mpn: str | None = Field(
        description="For alias_conflict: the MPN the page named that another drive goes by."
    )
    conflict_drive_id: UUID | None = Field(description="For alias_conflict: that other drive.")
    item_price_cents: int | None
    shipping_cents: int | None
    in_stock: bool
    reason: ReviewReason
    provenance: Provenance
    first_seen_at: datetime
    last_seen_at: datetime
    drive: Drive | None = Field(
        description="The drive its MPN names as recorded now, to set what was collected beside;"
        " null when it names none."
    )


class ListingFacts(Contract):
    """What pasted listing text says of an offer; anything it does not say is null."""

    title: str | None
    mpn: str | None
    capacity_gb: int | None
    condition: Condition | None
    brand: str | None
    item_price_cents: int | None


# Reading drives the way the Prices page does.

Sort = Literal[
    "unit-asc", "unit-desc", "total-asc", "total-desc",
    "capacity-asc", "capacity-desc", "checked-desc", "checked-asc",
]  # fmt: skip
RANGE_DAYS = (30, 90, 180)


class RangeQuery(Contract):
    """How a drive's price range is read: over range_days (30, 90 or 180), an offer unchecked for
    longer than recent_days taken to have ended at its last check."""

    model_config = ConfigDict(extra="forbid")
    recent_days: int = Field(default=7, ge=1, le=365, description="What checked recently means")
    range_days: int = Field(
        default=90,
        description="How far back each price range looks, in days.",
        json_schema_extra={"enum": list(RANGE_DAYS)},
    )

    @field_validator("range_days")
    @classmethod
    def a_period(cls, days: int) -> int:
        if days not in RANGE_DAYS:
            raise ValueError("Input should be 30, 90 or 180")
        return days


class DriveScope(Contract):
    """Which drives: those with an offer matching every filter given; choices within a filter
    are alternatives. Unknown is a value of every specification."""

    model_config = ConfigDict(extra="forbid")
    q: str = Field(default="", max_length=200, description="Words in a title, MPN or seller")
    brand: list[str] = Field(default=[], description="Brands, unknown for none named")
    capacity: list[Annotated[int, Field(gt=0)]] = Field(
        default=[],
        description="Capacity choices in decimal GB. Repeat the parameter for multiple choices.",
    )
    condition: list[Condition] = Field(
        default=[], description="Condition choices; repeat the parameter for multiple choices."
    )
    store: list[StoreKey] = Field(
        default=[], description="Source keys, not UUIDs; repeat for multiple stores."
    )
    media_type: MediaType | None = None
    form_factor: FormFactor | None = None
    interface: Interface | None = None
    recording_type: Recording | None = None
    intended_use: IntendedUse | Literal["unknown"] | None = None

    def scope(self) -> "DriveScope":
        """Just which drives, without anything a subclass asks besides."""
        return DriveScope(**{name: getattr(self, name) for name in DriveScope.model_fields})


class DriveQuery(RangeQuery, DriveScope):
    """Which drives to list, in what order, and which part of the list. Filters apply to offers:
    a drive is listed when any offer of it matches, and is shown by the cheapest of those in
    stock."""

    model_config = ConfigDict(extra="forbid")
    drive_id: UUID | None = Field(default=None, description="Only this drive, if it matches")
    max_total_cents: int | None = Field(
        default=None, ge=0, description="Maximum item price plus known shipping, in US cents."
    )
    in_stock: bool = Field(default=True, description="Only offers in stock; false for all")
    recent_only: bool = Field(default=False, description="Only offers checked recently")
    sort: Sort = Field(
        default="unit-asc",
        description="unit sorts by total dollars per TB; total includes known shipping; checked sorts by last check time.",
    )
    limit: int = Field(default=50, ge=1, le=500, description="Maximum drives in this page.")
    offset: int = Field(default=0, ge=0, description="Number of matching items to skip.")


# What a drive may need from a person: its specifications entered, or an offer of it in stock
# checked again (one not checked within recent_days).
DriveIssue = Literal["unknown_specifications", "stale"]


class CatalogDriveQuery(Contract):
    """Which of every drive to manage, and which part of the list. q: words any name an offer of
    it goes by contains (its title, MPN, its drive's other MPNs, who sells it); a drive they are
    the MPN or another MPN of comes first."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    q: str = Field(default="", max_length=200)
    issue: DriveIssue | None = Field(default=None, description="Only drives that need this")
    recent_days: int = Field(default=7, ge=1, le=365, description="What checked recently means")
    limit: int = Field(default=50, ge=1, le=500, description="Maximum drives in this page.")
    offset: int = Field(default=0, ge=0, description="Number of matching drives to skip.")


class PriceRange(Contract):
    """Where a drive's lowest item price has been over the days asked for, in cents: today's
    (null when no store has it in stock), the lowest and highest it has been, its average weighed
    by how long each price held, and how many days of prices there are."""

    today: int | None
    low: int
    high: int
    average: int
    days: int


class DriveRow(Contract):
    """A drive as the list shows it: by its cheapest matching offer in stock (else its cheapest
    matching offer), with every offer of it that matches, and the range of its price in the
    representative's condition. key: what the app opens the drive by."""

    key: str
    drive: Drive
    representative: OfferSummary
    offers: list[OfferSummary]
    range: PriceRange | None


class Choice[T](Contract):
    value: T
    drives: int


class FilterOptions(Contract):
    """What the filters can choose from: every option the catalogue has, each with how many drives
    choosing it would give, with the search and every other filter as asked but not its own
    group's, whichever page is shown."""

    brands: list[Choice[str]]
    capacities: list[Choice[int]]
    conditions: list[Choice[Condition]]


class Lowest(Contract):
    """The offers with the lowest total and the lowest total per terabyte among every offer that
    matches, in stock and checked recently."""

    total: list[UUID]
    unit: list[UUID]


class CatalogDrive(Contract):
    """A drive to manage: named by the title of the offer it is shown by (its cheapest in stock,
    else its cheapest), with how many offers it has and what it needs."""

    drive: Drive
    title: str
    offers: int
    issues: list[DriveIssue]


class DriveIssueCounts(Contract):
    unknown_specifications: int
    stale: int


class CatalogDrivePage(Contract):
    """A part of the drives to manage. total: drives that match; all: every drive; issues: how
    many of every drive need each thing."""

    items: list[CatalogDrive]
    total: int
    all: int
    issues: DriveIssueCounts
    limit: int
    offset: int


class DrivePage(Contract):
    """A part of the drive list. total: drives that match; offers: offers that match; sold_out:
    drives left out only because no store has them in stock. as_of: the moment recency and
    ranges are judged against."""

    items: list[DriveRow]
    total: int
    offers: int
    sold_out: int
    limit: int
    offset: int
    as_of: datetime
    lowest: Lowest
    filter_options: FilterOptions


class DriveDetail(Contract):
    """A drive with every offer of it, in every condition, and in each condition it is offered
    in, the range of its lowest item price over the days asked for (null when no offer of it was
    in stock then)."""

    drive: Drive
    offers: list[OfferSummary]
    ranges: dict[Condition, PriceRange | None]


class PriceQuery(Contract):
    """Prices of one drive's offers, or of one offer, in effect at any time from since to until:
    a window holds the price still holding as it opens. Oldest first, a part at a time."""

    model_config = ConfigDict(extra="forbid")
    drive_id: UUID | None = Field(
        default=None, description="Drive UUID. Supply exactly one of drive_id or offer_id."
    )
    offer_id: UUID | None = Field(
        default=None, description="Offer UUID. Supply exactly one of drive_id or offer_id."
    )
    since: AwareDatetime | None = Field(
        default=None,
        description="Inclusive window start. Includes the last price before this time for each offer to establish the opening value.",
    )
    until: AwareDatetime | None = Field(
        default=None, description="Inclusive window end; omit for no upper time bound."
    )
    limit: int = Field(
        default=500,
        ge=1,
        le=1000,
        description="Maximum observations in this page, including opening values.",
    )
    offset: int = Field(default=0, ge=0, description="Number of matching items to skip.")

    @model_validator(mode="after")
    def one_resource(self) -> "PriceQuery":
        if (self.drive_id is None) == (self.offer_id is None):
            raise ValueError("Name a drive_id or an offer_id, not both.")
        return self


class PriceRow(Observation):
    offer_id: UUID


class PricePage(Contract):
    items: list[PriceRow]
    total: int
    limit: int
    offset: int


class OfferQuery(Contract):
    """Which offers to list: of a store, of a drive, or those a person has to check by hand
    (entered by hand and not checked within recent_days), longest unchecked first."""

    model_config = ConfigDict(extra="forbid")
    store: StoreKey | None = None
    drive_id: UUID | None = None
    needs_recheck: bool = False
    recent_days: int = Field(default=7, ge=1, le=365)
