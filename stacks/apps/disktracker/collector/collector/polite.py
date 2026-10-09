"""Every request a source makes to a store goes through here: it identifies the collector,
fetches only what the site's robots.txt allows, and waits the site's Crawl-delay between
requests. Each site's rules are read at the start of a run or a preview, and kept for it."""

from typing import Any, Protocol
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import httpx

from collector.clock import Clock
from collector.errors import OutOfTime, SourceUnavailable
from collector.pacer import Pacer

AGENT = "disktracker-collector"
USER_AGENT = f"{AGENT}/0.1 (personal drive price tracker)"
RULES_LIFETIME_SECONDS = 24 * 3600


class Disallowed(SourceUnavailable):
    """robots.txt does not allow the collector to fetch this URL."""


def same_site(url: str, other: str) -> bool:
    """Whether two URLs are on one site: hosts compare without case or a leading www."""

    def host(value: str) -> str:
        return urlsplit(value).netloc.lower().removeprefix("www.")

    return host(url) == host(other)


def origin_of(url: str) -> str:
    """The site a URL is on. Hosts are case-insensitive: www.goHardDrive.com and
    www.goharddrive.com are one site."""
    return "{0.scheme}://{0.netloc}".format(urlsplit(url)).lower()


class Fetcher(Protocol):
    """What fetches a page: httpx itself, or a browser (collector.browser)."""

    def get(self, url: str, *, headers: dict[str, str]) -> httpx.Response: ...


class Pages(Protocol):
    """How a reader fetches a store's pages."""

    def get(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response: ...

    def get_if_present(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response | None: ...

    def sitemaps(self, url: str) -> list[str]: ...

    def crawl_delay(self, url: str) -> float: ...


class PoliteHttp:
    def __init__(self, http: Fetcher, pacer: Pacer, clock: Clock) -> None:
        self.http, self.pacer, self.clock = http, pacer, clock
        self.rules: dict[str, tuple[float, RobotFileParser]] = {}

    def get(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response:
        """The page at url; any failure to get it is SourceUnavailable."""
        response = self.get_if_present(url, params, min_delay)
        if response is None:
            raise SourceUnavailable(f"Not found: {url}")
        return response

    def get_if_present(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response | None:
        """The page at url, or None when the site says it does not exist (404). min_delay
        spaces requests to a site that asks for no crawl delay (or too short a one)."""
        full = str(httpx.URL(url, params=params))
        origin = origin_of(full)
        rules = self._rules(origin)
        if not rules.can_fetch(AGENT, full):
            raise Disallowed(f"robots.txt disallows {full}")
        delay = max(float(rules.crawl_delay(AGENT) or 0), min_delay)
        self.pacer.wait_turn(origin, delay or None)
        try:
            response = self.http.get(full, headers={"User-Agent": USER_AGENT})
            if response.status_code == 404:
                return None
            return response.raise_for_status()
        except httpx.HTTPError as error:
            raise SourceUnavailable(str(error)) from error

    def forget_rules(self) -> None:
        """Read every site's robots.txt again when it is next needed. Rules are kept only to
        save asking again before each page of one run; nothing, a refusal least of all, should
        outlast the run or the preview that learnt it."""
        self.rules.clear()

    def sitemaps(self, url: str) -> list[str]:
        """The sitemaps the site's robots.txt names."""
        return list(self._rules(origin_of(url)).site_maps() or [])

    def crawl_delay(self, url: str) -> float:
        """The seconds the site's robots.txt asks for between requests; 0 when it asks none."""
        return float(self._rules(origin_of(url)).crawl_delay(AGENT) or 0)

    def _rules(self, origin: str) -> RobotFileParser:
        cached = self.rules.get(origin)
        if cached and self.clock.monotonic() - cached[0] < RULES_LIFETIME_SECONDS:
            return cached[1]
        rules = RobotFileParser()
        try:
            response = self.http.get(f"{origin}/robots.txt", headers={"User-Agent": USER_AGENT})
        except httpx.HTTPError as error:
            raise SourceUnavailable(f"robots.txt: {error}") from error
        if response.status_code >= 500:
            raise SourceUnavailable(f"robots.txt: HTTP {response.status_code}")
        if response.status_code in (401, 403):
            rules.parse(["User-agent: *", "Disallow: /"])
        elif response.is_success:
            rules.parse(response.text.splitlines())
        else:
            # No robots.txt (404 and the like) means no restrictions.
            rules.parse([])
        self.rules[origin] = (self.clock.monotonic(), rules)
        return rules


class TimedPages:
    """A store's pages, fetched only while there is time: once seconds have passed since it
    was made, the next request is refused with how far the reading got. A request under way,
    or waiting its crawl delay, is not cut short."""

    def __init__(self, pages: Pages, clock: Clock, seconds: float) -> None:
        self.pages, self.clock, self.seconds = pages, clock, seconds
        self.started = clock.monotonic()
        self.requests = 0
        self.last = ""

    def _take(self, url: str) -> None:
        if self.clock.monotonic() - self.started > self.seconds:
            raise OutOfTime(
                f"out of time after {self.seconds:g} seconds: {self.requests} requests made,"
                f" the last for {self.last}"
            )
        self.requests += 1
        self.last = url

    def get(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response:
        self._take(url)
        return self.pages.get(url, params, min_delay)

    def get_if_present(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response | None:
        self._take(url)
        return self.pages.get_if_present(url, params, min_delay)

    def sitemaps(self, url: str) -> list[str]:
        return self.pages.sitemaps(url)

    def crawl_delay(self, url: str) -> float:
        return self.pages.crawl_delay(url)


def json_of(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as error:
        raise SourceUnavailable(str(error)) from error
