"""HTTP input contracts; database and domain code do not depend on FastAPI."""

import re
from typing import Annotated, Any, Literal

from croniter import croniter
from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    ValidationInfo,
    field_validator,
)

from disktracker.kinds import KINDS
from disktracker.mpn import normalize_mpn
from disktracker.specifications import Specifications

Cents = Annotated[int, Field(strict=True, ge=0, le=1_000_000_000)]
# Whole decimal gigabytes (1 TB = 1000 GB), up to 10 PB.
Capacity = Annotated[int, Field(strict=True, gt=0, le=10_000_000)]
NormalizedMpn = Annotated[str, AfterValidator(normalize_mpn), Field(min_length=1, max_length=100)]
Condition = Literal["new", "manufacturer_recertified", "refurbished", "used"]
# A store's key: the key of the source offers are recorded under; Other (named by seller) is
# for one-off stores.
StoreKey = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[a-z0-9]+$")]


class ObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    in_stock: bool = True
    item_price_cents: Cents | None = Field(default=None, validate_default=True)
    shipping_cents: Cents | None = 0
    notes: str = Field(default="", max_length=2000)
    observed_at: AwareDatetime | None = None

    @field_validator("item_price_cents")
    @classmethod
    def priced_when_in_stock(cls, value: int | None, info: ValidationInfo) -> int | None:
        if value is None and info.data.get("in_stock", True):
            raise ValueError("Enter the item price.")
        # A store writes 0 for what it sells only by quote; nothing is sold for nothing.
        if value == 0:
            raise ValueError("Enter a price above zero.")
        return value


class PriceInput(ObservationInput):
    """One observed price; the offer is identified by MPN + store + seller + condition."""

    mpn: NormalizedMpn
    store: StoreKey
    seller: str = Field(default="", max_length=120)
    condition: Condition
    title: str | None = Field(default=None, min_length=1, max_length=160)
    url: HttpUrl | None = None
    capacity_gb: Capacity | None = None

    @field_validator("seller")
    @classmethod
    def other_stores_need_a_seller(cls, seller: str, info: ValidationInfo) -> str:
        if info.data.get("store") == "other" and not seller:
            raise ValueError("Name the seller when the store is Other.")
        return seller


class ScrapedInput(ObservationInput):
    """An offer as a collector saw it at its source, which is the store it is recorded under;
    MPN or condition may be missing until reviewed."""

    source: StoreKey
    url: HttpUrl
    title: str = Field(min_length=1, max_length=160)
    seller: str = Field(default="", max_length=120)
    mpn: NormalizedMpn | None = None
    aliases: list[NormalizedMpn] = []
    condition: Condition | None = None
    capacity_gb: Capacity | None = None
    # What the source says about the drive; it fills in only values nobody has entered.
    specifications: Specifications | None = None
    brand: str | None = Field(default=None, min_length=1, max_length=60)

    def as_price(self) -> PriceInput:
        return PriceInput.model_validate(
            self.model_dump(exclude={"source", "aliases", "specifications", "brand"})
            | {"url": str(self.url), "store": self.source}
        )


class Resolution(BaseModel):
    """What a reviewer decided a queued scraped offer is."""

    model_config = ConfigDict(extra="forbid")
    mpn: NormalizedMpn
    condition: Condition
    capacity_gb: Capacity | None = None


class OfferEdit(BaseModel):
    """Details that can change in place; MPN, store, seller and condition identify the offer."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str | None = Field(default=None, min_length=1, max_length=160)
    url: HttpUrl | None = None


class AliasInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mpn: NormalizedMpn


class DriveSpecifications(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    capacity_gb: Capacity
    specifications: Specifications
    # The drive's maker, corrected by hand. Left out, it stays as it is; blank, it is unknown
    # again, until a source names it.
    brand: str | None = Field(default=None, max_length=60)

    @field_validator("brand")
    @classmethod
    def blank_is_unknown(cls, brand: str | None) -> str | None:
        return brand or None


Count = Annotated[int, Field(strict=True, ge=0)]


class CollectorRun(BaseModel):
    """What one collector run of one source did, as the collector reports it."""

    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1, max_length=40)
    started_at: AwareDatetime
    finished_at: AwareDatetime
    completed: bool
    seen: Count
    recorded: Count
    queued: Count
    ignored: Count
    failed: Count
    rechecked: Count
    recheck_failed: Count
    # The run ended early because it was asked to stop, rather than failing.
    stopped: bool = False


class Activity(BaseModel):
    """How far a run in progress has got, as the collector says while it runs."""

    model_config = ConfigDict(extra="forbid")
    source: str = Field(min_length=1, max_length=40)
    started_at: AwareDatetime
    seen: Count
    recorded: Count
    queued: Count
    ignored: Count
    failed: Count


class ActivityAnswer(BaseModel):
    """What the collector is told when it says how far a run has got. stop: the run was asked
    to stop, so it should end here."""

    stop: bool


class RunningActivity(Activity):
    """A run in progress, and when the collector last said how far it had got."""

    updated_at: AwareDatetime


class CollectorStatus(BaseModel):
    """What the collector is doing: when it was last heard from (never: None), the runs in
    progress, and the keys of the sources waiting to run, in the order they will."""

    seen_at: AwareDatetime | None
    running: list[RunningActivity]
    waiting: list[str]


class ListingText(BaseModel):
    """Text a person copied from a listing page."""

    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1, max_length=5000, pattern=r"\S")


# The kind of a store: one the collector reads, or one entered by hand (disktracker.kinds).
SourceKind = str
COLLECTED_URL = re.compile(r"^https?://[^\s/]+\S*$")


# What allows collecting from a source: recorded so the decision is visible, not enforced.
SourceBasis = Literal["permission", "terms_allow", "open_api", "unconfirmed"]
# How the collector fetches a source's pages: itself, or through a headless browser
# (FlareSolverr) for stores that only answer browsers.
SourceTransport = Literal["direct", "browser"]


class SourceInput(BaseModel):
    """A store offers are recorded under: its kind (how the collector reads it, or entered by
    hand), its address, and when it is collected. Its key is fixed from its name."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=80, pattern=r"[A-Za-z0-9]")
    kind: SourceKind
    # Needed to collect a store; optional for one entered by hand.
    base_url: str = Field(default="", max_length=2083)
    # Checked against the kind's description by disktracker.kinds.
    settings: dict[str, Any] = {}
    schedule: str = Field(default="0 */8 * * *", max_length=100)
    enabled: bool = True
    transport: SourceTransport = "direct"
    basis: SourceBasis = "unconfirmed"
    notes: str = Field(default="", max_length=2000)

    @field_validator("kind")
    @classmethod
    def a_known_kind(cls, kind: str) -> str:
        if kind not in KINDS:
            raise ValueError("Choose a type.")
        return kind

    @field_validator("base_url")
    @classmethod
    def an_address_to_collect_from(cls, base_url: str, info: ValidationInfo) -> str:
        collected = KINDS.get(info.data.get("kind", ""), {}).get("collected", True)
        if (base_url or collected) and not COLLECTED_URL.match(base_url):
            raise ValueError("Enter the store's address, starting http:// or https://.")
        return base_url

    @field_validator("schedule")
    @classmethod
    def five_field_cron(cls, schedule: str) -> str:
        if len(schedule.split()) != 5 or not croniter.is_valid(schedule):
            raise ValueError("Enter a cron schedule, e.g. 0 3 * * *.")
        return schedule


class SourcePreviewInput(SourceInput):
    """A source to try, saved or not. page_url: one of its pages to read instead of those its
    sitemap lists, so its settings can be tried on a page known to offer a drive."""

    page_url: str = Field(default="", max_length=2083)

    @field_validator("page_url")
    @classmethod
    def a_page_of_a_sitemap_source(cls, page_url: str, info: ValidationInfo) -> str:
        if page_url and not KINDS.get(info.data.get("kind", ""), {}).get("page_test"):
            raise ValueError("This kind of store cannot be tested on one page.")
        if page_url and not COLLECTED_URL.match(page_url):
            raise ValueError("Enter the page's address, starting http:// or https://.")
        return page_url


class SourceInspectionInput(BaseModel):
    """A link to one product page of a store, to find out how the store would be read."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    url: str = Field(max_length=2083, pattern=r"^https?://[^\s/]+\S*$")
    transport: SourceTransport = "direct"


def a_regular_expression(pattern: str) -> str:
    try:
        re.compile(pattern)
    except re.error as error:
        raise ValueError(f"Enter a regular expression ({error}).") from error
    return pattern


class ConditionRule(BaseModel):
    """Text matching the pattern (a case-insensitive regular expression) names the condition;
    rules are read in order and the first match wins."""

    model_config = ConfigDict(extra="forbid")
    pattern: Annotated[
        str, Field(min_length=1, max_length=200), AfterValidator(a_regular_expression)
    ]
    condition: Condition
