"""Stand-ins for the collector's own ports (Clock, Reader, Disktracker), for unit tests.

Only interfaces the collector owns are faked; third-party code is never replaced."""

from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from listing_text.readers import ConditionRules

from collector.errors import DisktrackerUnavailable, SourceUnavailable
from collector.models import Posted, RunSummary, ScrapedOffer
from collector.ports import Description, Inspection, Rechecked, Site, Tell
from disktracker_api.models import ListingSummary, SourceView


class FakeClock:
    """Time that only moves when something sleeps."""

    def __init__(self, now: datetime = datetime(2026, 9, 26, 12, tzinfo=UTC)) -> None:
        self.current = now
        self.elapsed = 0.0
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return self.current

    def monotonic(self) -> float:
        return self.elapsed

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.elapsed += seconds

    def advance(self, seconds: float) -> None:
        self.elapsed += seconds


def offer(url: str, *, item_price_cents: int | None = 29999, in_stock: bool = True) -> ScrapedOffer:
    return ScrapedOffer(
        source="goharddrive",
        url=url,
        title=f"Drive at {url}",
        mpn="ST18000NM000J",
        condition="new",
        capacity_gb=18000,
        item_price_cents=item_price_cents,
        in_stock=in_stock,
    )


class FakeReader:
    """Reads a store whose offers, product URLs and recheck results are set by the test. When
    unavailable is set, the store fails after handing over its offers. It keeps the sites it
    was given to read."""

    def __init__(
        self,
        offers: list[ScrapedOffer] | None = None,
        journal: list[str] | None = None,
        unavailable: str | None = None,
        rechecks: dict[str, ScrapedOffer | SourceUnavailable] | None = None,
    ) -> None:
        self.listed = offers or []
        self.journal = journal if journal is not None else []
        self.unavailable = unavailable
        self.rechecks = rechecks or {}
        self.sites: list[Site[Mapping[str, Any]]] = []
        self.description = Description("Fake", ())

    def settings(self, saved: Mapping[str, Any]) -> Mapping[str, Any]:
        """As saved, but for the keys a test asks it to trip on."""
        if "missing" in saved:
            raise KeyError(saved["missing"])
        if "unreadable" in saved:
            raise ValueError(saved["unreadable"])
        return saved

    def offers(self, site: Site[Mapping[str, Any]]) -> Iterator[ScrapedOffer]:
        self.sites.append(site)
        for listed in self.listed:
            self.journal.append(f"read {listed.url}")
            yield listed
        if self.unavailable:
            raise SourceUnavailable(self.unavailable)

    def sample(self, site: Site[Mapping[str, Any]], tell: Tell) -> Iterator[ScrapedOffer]:
        return self.offers(site)

    def recheck(
        self, listings: Sequence[ListingSummary], site: Site[Mapping[str, Any]]
    ) -> Iterator[Rechecked]:
        """The listings on https://store.test/, each as the test set its product to be."""
        for listing in listings:
            if not (listing.url or "").startswith("https://store.test/"):
                continue
            found = self.rechecks[(listing.url or "").removeprefix("https://store.test/")]
            if isinstance(found, SourceUnavailable):
                yield Rechecked(listing, None, str(found))
            else:
                yield Rechecked(listing, found)

    def inspect(self, url: str, page: str, site: Site[None]) -> Inspection:
        return Inspection([], [])


Due = list[SourceView] | DisktrackerUnavailable


class FakeDisktracker:
    """Records every post; answers each with the next status, or "recorded" with an id. due is
    what it says is due every time it is asked; polls scripts successive answers instead, the
    last repeating. It keeps the progress it is told of, asks the run to stop from the
    stop_from-th time on, and cannot take progress at all when progressing is set. on_post is
    called as each offer is posted, for a test to move its clock."""

    def __init__(
        self,
        statuses: list[str] | None = None,
        listings: list[ListingSummary] | DisktrackerUnavailable | None = None,
        journal: list[str] | None = None,
        reporting: DisktrackerUnavailable | None = None,
        due: Due | None = None,
        polls: list[Due] | None = None,
        conditions: ConditionRules = (),
        stop_from: int | None = None,
        progressing: DisktrackerUnavailable | None = None,
        on_post: Callable[[], None] = lambda: None,
    ) -> None:
        self.stop_from, self.progressing, self.on_post = stop_from, progressing, on_post
        self.progress: list[tuple[str, datetime, dict[str, int]]] = []
        self.polls = polls or [due if due is not None else []]
        self.conditions = conditions
        self.statuses = list(statuses or [])
        self.reporting = reporting
        self.reports: list[tuple[RunSummary, datetime, datetime]] = []
        self.known = listings if listings is not None else []
        self.journal = journal if journal is not None else []
        self.posted: list[tuple[ScrapedOffer, datetime]] = []
        self.asked_for: list[str] = []

    def due_sources(self) -> list[SourceView]:
        self.journal.append("due sources")
        due = self.polls[0] if len(self.polls) == 1 else self.polls.pop(0)
        if isinstance(due, DisktrackerUnavailable):
            raise due
        return due

    def condition_rules(self) -> ConditionRules:
        self.journal.append("condition rules")
        return self.conditions

    def listings(self, store: str) -> list[ListingSummary]:
        self.asked_for.append(store)
        if isinstance(self.known, DisktrackerUnavailable):
            raise self.known
        return self.known

    def post_scraped(self, offer: ScrapedOffer, observed_at: datetime) -> Posted:
        self.journal.append(f"post {offer.url}")
        self.posted.append((offer, observed_at))
        self.on_post()
        status = self.statuses.pop(0) if self.statuses else "recorded"
        return Posted(status, UUID(int=len(self.posted)) if status == "recorded" else None)

    def report_run(self, summary: RunSummary, started_at: datetime, finished_at: datetime) -> None:
        if self.reporting is not None:
            raise self.reporting
        self.reports.append((summary, started_at, finished_at))

    def report_progress(self, source: str, started_at: datetime, counts: dict[str, int]) -> bool:
        if self.progressing is not None:
            raise self.progressing
        self.progress.append((source, started_at, dict(counts)))
        return self.stop_from is not None and len(self.progress) >= self.stop_from
