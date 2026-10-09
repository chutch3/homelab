"""The interfaces the collector's services depend on; adapters implement them."""

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from listing_text.readers import ConditionRules

from collector.models import Posted, RunSummary, ScrapedOffer, Store
from collector.polite import Pages
from disktracker_api.models import ListingSummary, SourceView

# Told, in sentences for whoever is setting a source up, what was read of a store and why a
# page gave no offer.
Tell = Callable[[str], None]


def tell_nobody(_note: str) -> None:
    """Nobody is watching a scheduled run read; what it does is in its log."""


@dataclass(frozen=True)
class Site[S]:
    """One source as a reader is given it: how its pages are fetched, its store, and its
    settings as the reader read them."""

    http: Pages
    store: Store
    settings: S


@dataclass(frozen=True)
class Setting:
    """One thing a kind of source needs to know about a store: how the Admin form asks for it
    and how disktracker checks it. A text setting left blank is "", a list is empty, a flag is
    off; required means it cannot be left so."""

    name: str
    label: str
    # text, list (of texts) or flag
    type: str = "text"
    required: bool = False
    description: str = ""
    placeholder: str = ""
    # The group of settings it is asked for among; "" for none.
    group: str = ""
    # What a text must look like, and what to say when it does not.
    pattern: str = ""
    pattern_message: str = ""
    # The text is itself a regular expression; capturing, one with a group.
    regex: bool = False
    capturing: bool = False
    # Another setting that, once given, makes this one required.
    needs: str = ""


@dataclass(frozen=True)
class Group:
    """Settings asked for together, apart from the rest, with what they are for."""

    name: str
    label: str
    help: str


@dataclass(frozen=True)
class Description:
    """A kind of source as disktracker presents it: its name and its settings."""

    label: str
    settings: tuple[Setting, ...]
    groups: tuple[Group, ...] = ()


@dataclass(frozen=True)
class Rechecked:
    """A known offer checked again on its product page: the offer as the page shows it now, or,
    when the page could not be fetched, why."""

    listing: ListingSummary
    offer: ScrapedOffer | None
    error: str = ""


@dataclass(frozen=True)
class Fact:
    """One thing worth knowing about a store before deciding to collect it."""

    label: str
    value: str


@dataclass(frozen=True)
class Reading:
    """One way a kind of source would read a store, worked out from one of its pages: the
    settings, as disktracker saves them; why they were chosen, in sentences; the offers they
    read, the one the page is for first; and whether the page's own product was among them
    (linked), which is what shows the settings read that page and not just the store."""

    settings: dict[str, Any]
    evidence: list[str]
    offers: list[ScrapedOffer]
    linked: bool = True
    # How much there is to the store, read with these settings; and how many requests a run
    # of it would make, when that can be told, for saying how long one would take.
    summary: list[Fact] = field(default_factory=list)
    requests: int | None = None


@dataclass(frozen=True)
class Inspection:
    """What a reader makes of a page of a store it has not been set up for: the ways it would
    read the store, and what it looked for and did not find."""

    readings: list[Reading]
    notes: list[str]


class Reader[S](Protocol):
    """Reads one kind of store. A reader is made once and reads any number of sources: each
    call is given the site to read. Everything particular to its kind of store is the
    reader's: how its settings are read, how its offers are, and how a store of its kind is
    told from one of its pages."""

    # What this kind of source is called and the settings it has. disktracker checks a
    # store's settings against it and draws its form from it; settings() reads exactly these.
    description: Description

    def settings(self, saved: Mapping[str, Any]) -> S:
        """A source's settings as saved on disktracker, read for this kind of store."""
        ...

    def offers(self, site: Site[S]) -> Iterable[ScrapedOffer]:
        """Offers as they are read, so each can be posted before the next is fetched."""
        ...

    def sample(self, site: Site[S], tell: Tell) -> Iterable[ScrapedOffer]:
        """The offers of just enough of the store to show one, for trying its settings."""
        ...

    def recheck(self, listings: Sequence[ListingSummary], site: Site[S]) -> Iterable[Rechecked]:
        """Each of these known offers that is on one of this store's product pages, as that
        page shows it now, in the order given; an offer whose URL is no product page of the
        store is passed over. A page several of them share is fetched once."""
        ...

    def inspect(self, url: str, page: str, site: Site[None]) -> Inspection:
        """Whether the page at url, already fetched, is a store of this kind's, and how the
        store would be read. The site has no settings yet: working them out is the point. It
        may fetch a little more of the store to do so."""
        ...


@runtime_checkable
class ReadsOnePage[S](Protocol):
    """A reader that can read one page of a store alone, so settings can be tried on a page
    known to offer a drive. Not every kind of store is read page by page."""

    def page_offers(self, url: str, site: Site[S], tell: Tell) -> Iterable[ScrapedOffer]:
        """The offers on the page at url, wherever the store itself would lead."""
        ...


class Disktracker(Protocol):
    def due_sources(self) -> list[SourceView]:
        """The sources due to run now: their schedule has fired since their last run, or they
        were asked to run (switched on or not)."""
        ...

    def condition_rules(self) -> ConditionRules:
        """Which text names which condition, in order: the first rule that matches wins."""
        ...

    def listings(self, store: str) -> list[ListingSummary]: ...

    def post_scraped(self, offer: ScrapedOffer, observed_at: datetime) -> Posted: ...

    def report_progress(self, source: str, started_at: datetime, counts: dict[str, int]) -> bool:
        """Say how far the run of a source that started then has got. Whether the run has been
        asked to stop."""
        ...

    def report_run(
        self, summary: RunSummary, started_at: datetime, finished_at: datetime
    ) -> None: ...
