"""Collection's public contract: what its routes accept and what they return. Clients are
generated from these."""

import re
from datetime import datetime
from typing import Annotated, ClassVar, Literal
from uuid import UUID

from croniter import croniter
from pydantic import (
    AwareDatetime,
    ConfigDict,
    Field,
    ValidationInfo,
    field_validator,
    model_validator,
)

from disktracker.collection.settings import (
    KINDS,
    Kind,
    ManualSettings,
    SapCommerceSettings,
    Settings,
    ShopifySettings,
    SitemapSettings,
)
from disktracker.contract import Contract

Count = Annotated[int, Field(strict=True, ge=0)]


RunStatus = Literal["running", "completed", "failed", "stopped", "abandoned"]
EndStatus = Literal["running", "completed", "failed", "stopped"]


class RunStart(Contract):
    """A run as it starts. id: chosen by the collector, so a start whose answer was lost can be
    sent again."""

    model_config = ConfigDict(extra="forbid")
    id: UUID
    source: str = Field(
        min_length=1,
        max_length=40,
        description="Stable source key from GET /api/sources, not its UUID.",
    )
    started_at: AwareDatetime


class RunCounts(Contract):
    """What a run has done so far: offers seen, and what became of them; offers no longer
    listed, checked again, and those that could not be."""

    model_config = ConfigDict(extra="forbid")
    seen: Count
    recorded: Count
    queued: Count
    ignored: Count
    failed: Count
    rechecked: Count = 0
    recheck_failed: Count = 0


class RunUpdate(RunCounts):
    """How far a run has got, or how it ended: running with its counts so far, or completed,
    failed or stopped (asked to stop) with when it finished. Counts are what it has done in all,
    not since it last said."""

    status: EndStatus = "running"
    finished_at: AwareDatetime | None = Field(
        default=None,
        description="Required for completed, failed or stopped runs; must be omitted or null while running.",
    )
    reason: str | None = Field(
        default=None,
        max_length=500,
        description="What went wrong, as the person running the collector would want to read it; only for a failed run.",
    )

    @field_validator("reason")
    @classmethod
    def only_a_failure_says_why(cls, reason: str | None, info: ValidationInfo) -> str | None:
        if reason is not None and info.data.get("status") != "failed":
            raise ValueError("Only a failed run says why.")
        return reason

    @model_validator(mode="after")
    def ended_when_it_ended(self) -> "RunUpdate":
        if (self.status == "running") != (self.finished_at is None):
            raise ValueError("A run that has ended says when; one still running does not.")
        return self


class Run(RunCounts):
    """A run. stop_requested: its source was asked to stop since it started, so it should end
    here. reason: why it did not complete, when known: as its collector said for a failed run,
    as disktracker found it for an abandoned one."""

    id: UUID
    source: str
    status: RunStatus
    started_at: AwareDatetime
    updated_at: AwareDatetime
    finished_at: AwareDatetime | None
    reason: str | None
    stop_requested: bool


class RunQuery(Contract):
    """Which runs to read, oldest first: of a source, in a status, ended since a moment; or the
    latest run of each source, by source."""

    model_config = ConfigDict(extra="forbid")
    source: str | None = Field(default=None, description="Filter by source key, not source UUID.")
    status: RunStatus | None = None
    finished_since: AwareDatetime | None = Field(
        default=None, description="Only runs finished at or after this timezone-aware timestamp."
    )
    latest_per_source: bool = Field(
        default=False,
        description="Return only the latest matching run per source, ordered by source key.",
    )


class Heartbeat(Contract):
    """A collector saying it is alive, with the runs it has: none when it has nothing to do. Any
    other run still marked running is abandoned."""

    model_config = ConfigDict(extra="forbid")
    runs: list[UUID] = Field(
        default=[],
        description="All runs currently owned by the worker. Any other running run is abandoned; send an empty list while idle.",
    )


class HeartbeatAnswer(Contract):
    seen_at: AwareDatetime


class CollectorStatus(Contract):
    """What the collector is doing: when it was last heard from (never: None), the runs in
    progress, and the keys of the sources waiting to run, in the order they will."""

    seen_at: AwareDatetime | None
    running: list[Run]
    waiting: list[str]


class SourceQuery(Contract):
    """due: only the sources due to run now, in the order to run them. Reading changes nothing."""

    model_config = ConfigDict(extra="forbid")
    due: bool = Field(
        default=False,
        description="Only sources due now, ordered for collection; reading does not start a run.",
    )


COLLECTED_URL = re.compile(r"^https?://[^\s/]+\S*$")


# What allows collecting from a source: recorded so the decision is visible. Only permission
# changes what the collector may do: with it, a source may be told not to obey robots.txt.
SourceBasis = Literal["permission", "terms_allow", "open_api", "unconfirmed"]


# How the collector fetches a source's pages: itself, or through a headless browser
# (FlareSolverr) for stores that only answer browsers.
SourceTransport = Literal["direct", "browser"]


SETTINGS = "Reader-specific fields, as GET /api/source-kinds describes them."


class SourceBase(Contract):
    """A store offers are recorded under: its kind (how the collector reads it, or entered by
    hand), its address, and when it is collected. Its key is fixed from its name."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    of: ClassVar[Kind]
    name: str = Field(min_length=1, max_length=80, pattern=r"[A-Za-z0-9]")
    kind: str = Field(
        description="Reader kind from GET /api/source-kinds, or manual for prices entered by hand."
    )
    # Needed to collect a store; optional for one entered by hand.
    base_url: str = Field(
        default="",
        max_length=2083,
        description="Store HTTP(S) base URL, required for collected kinds; optional for manual sources.",
    )
    settings: Settings
    schedule: str = Field(
        default="0 */8 * * *",
        max_length=100,
        description="Five-field cron schedule evaluated in UTC; default runs every eight hours.",
    )
    enabled: bool = True
    transport: SourceTransport = "direct"
    basis: SourceBasis = "unconfirmed"
    obey_robots: bool = Field(
        default=True,
        description="False lets the collector read pages robots.txt disallows; only with basis permission.",
    )
    notes: str = Field(default="", max_length=2000)

    @field_validator("base_url")
    @classmethod
    def an_address_to_collect_from(cls, base_url: str) -> str:
        if (base_url or cls.of.collected) and not COLLECTED_URL.match(base_url):
            raise ValueError("Enter the store's address, starting http:// or https://.")
        return base_url

    @field_validator("obey_robots")
    @classmethod
    def ignored_only_with_permission(cls, obey_robots: bool, info: ValidationInfo) -> bool:
        if not obey_robots and info.data.get("basis") != "permission":
            raise ValueError("robots.txt can be ignored only with permission granted.")
        return obey_robots

    @field_validator("schedule")
    @classmethod
    def five_field_cron(cls, schedule: str) -> str:
        if len(schedule.split()) != 5 or not croniter.is_valid(schedule):
            raise ValueError("Enter a cron schedule, e.g. 0 3 * * *.")
        return schedule


class CollectedSourceBase(SourceBase):
    """A store the collector reads, which it cannot without an address."""

    base_url: str = Field(max_length=2083, description="Store HTTP(S) base URL.")


class ManualSourceInput(SourceBase):
    of = KINDS["manual"]
    kind: Literal["manual"]
    settings: ManualSettings = Field(default_factory=ManualSettings, description=SETTINGS)


class ShopifySourceInput(CollectedSourceBase):
    of = KINDS["shopify"]
    kind: Literal["shopify"]
    settings: ShopifySettings = Field(description=SETTINGS)


class SitemapSourceInput(CollectedSourceBase):
    of = KINDS["sitemap"]
    kind: Literal["sitemap"]
    settings: SitemapSettings = Field(default_factory=SitemapSettings, description=SETTINGS)


class SapCommerceSourceInput(CollectedSourceBase):
    of = KINDS["sap_commerce"]
    kind: Literal["sap_commerce"]
    settings: SapCommerceSettings = Field(description=SETTINGS)


# A source as it is entered: the fields of its kind, chosen by kind.
SourceInput = Annotated[
    ManualSourceInput | ShopifySourceInput | SitemapSourceInput | SapCommerceSourceInput,
    Field(discriminator="kind"),
]


class PagePreview(SourceBase):
    """A source to try, saved or not. page_url: one of its pages to read instead of those its
    sitemap lists, so its settings can be tried on a page known to offer a drive."""

    page_url: str = Field(default="", max_length=2083)

    @field_validator("page_url")
    @classmethod
    def a_page_of_a_sitemap_source(cls, page_url: str) -> str:
        if page_url and not cls.of.page_test:
            raise ValueError("This kind of store cannot be tested on one page.")
        if page_url and not COLLECTED_URL.match(page_url):
            raise ValueError("Enter the page's address, starting http:// or https://.")
        return page_url


class ManualSourcePreviewInput(ManualSourceInput, PagePreview):
    pass


class ShopifySourcePreviewInput(ShopifySourceInput, PagePreview):
    pass


class SitemapSourcePreviewInput(SitemapSourceInput, PagePreview):
    pass


class SapCommerceSourcePreviewInput(SapCommerceSourceInput, PagePreview):
    pass


SourcePreviewInput = Annotated[
    ManualSourcePreviewInput
    | ShopifySourcePreviewInput
    | SitemapSourcePreviewInput
    | SapCommerceSourcePreviewInput,
    Field(discriminator="kind"),
]


class SourceInspectionInput(Contract):
    """A link to one product page of a store, to find out how the store would be read."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    url: str = Field(max_length=2083, pattern=r"^https?://[^\s/]+\S*$")
    transport: SourceTransport = "direct"


# What the routes return.


class PreviewOffer(Contract):
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


class PreviewVerdict(Contract):
    """What disktracker would do with the offer: record it, hold it for review, or ignore it."""

    outcome: Literal["recorded", "review", "ignored"]
    reason: str | None


class SourcePreview(Contract):
    # found: an offer was read. nothing: the store was read but no drive found. failed: the
    # store could not be read, for the reason given.
    status: Literal["found", "nothing", "failed"]
    reason: str | None
    offer: PreviewOffer | None
    verdict: PreviewVerdict | None
    # What the collector read on the way, and why a page gave no offer, in sentences.
    notes: list[str] = []


class SettingView(Contract):
    """One thing a kind of store needs to know, as the form asks for it. Its rules are checked
    when a source is entered (disktracker.collection.settings)."""

    name: str
    label: str
    type: Literal["text", "list", "flag"]
    required: bool
    description: str
    placeholder: str
    # The group of settings it is asked for among; "" for none.
    group: str


class SettingGroupView(Contract):
    name: str
    label: str
    help: str


class SourceKindView(Contract):
    kind: str
    label: str
    # Read by the collector; a store entered by hand is not.
    collected: bool
    # One of its pages can be read alone to test it.
    page_test: bool
    groups: list[SettingGroupView]
    settings: list[SettingView]


class StoreFact(Contract):
    """One thing worth knowing about a store before deciding to collect it."""

    label: str
    value: str


class CandidateBase(Contract):
    """One way of reading the store a link is from: the kind of source and its settings, why
    they were chosen, how many offers they read from the page, the first of them, and what
    disktracker would do with it."""

    kind: str
    settings: Settings
    evidence: list[str]
    offers: int
    offer: PreviewOffer
    verdict: PreviewVerdict
    # How much there is to the store read this way, and how long a run of it would take.
    summary: list[StoreFact] = []


class ShopifyCandidate(CandidateBase):
    kind: Literal["shopify"]
    settings: ShopifySettings


class SitemapCandidate(CandidateBase):
    kind: Literal["sitemap"]
    settings: SitemapSettings


class SapCommerceCandidate(CandidateBase):
    kind: Literal["sap_commerce"]
    settings: SapCommerceSettings


InspectionCandidate = Annotated[
    ShopifyCandidate | SitemapCandidate | SapCommerceCandidate, Field(discriminator="kind")
]


class SourceInspection(Contract):
    # found: at least one way of reading the page gave a drive. nothing: none did. failed: the
    # page could not be read, for the reason given.
    status: Literal["found", "nothing", "failed"]
    reason: str | None
    # The store the link is from, as a source's address.
    base_url: str
    candidates: list[InspectionCandidate]
    # What was looked for on the page and not found.
    notes: list[str]


class SourceViewBase(Contract):
    id: UUID
    # What its prices and runs are recorded under; fixed when the source is created.
    key: str = Field(
        description="Stable source key used by prices and runs; distinct from this source UUID."
    )
    name: str
    kind: str
    settings: Settings
    base_url: str
    schedule: str
    enabled: bool
    transport: SourceTransport
    basis: SourceBasis
    obey_robots: bool
    notes: str
    # When the schedule next falls due, in UTC; null while the source is switched off.
    next_run_at: datetime | None


class ManualSourceView(SourceViewBase):
    kind: Literal["manual"]
    settings: ManualSettings


class ShopifySourceView(SourceViewBase):
    kind: Literal["shopify"]
    settings: ShopifySettings


class SitemapSourceView(SourceViewBase):
    kind: Literal["sitemap"]
    settings: SitemapSettings


class SapCommerceSourceView(SourceViewBase):
    kind: Literal["sap_commerce"]
    settings: SapCommerceSettings


# A source as the API shows it: the fields of its kind, chosen by kind.
SourceView = Annotated[
    ManualSourceView | ShopifySourceView | SitemapSourceView | SapCommerceSourceView,
    Field(discriminator="kind"),
]
