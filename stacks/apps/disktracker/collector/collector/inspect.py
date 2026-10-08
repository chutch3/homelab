"""Inspecting a link: from one product page of a store, which kinds of source would read the
store and with what settings, each tried on that page. It is how a store disktracker does not
read yet is set up without working its settings out by hand. Nothing is kept.

The page is fetched once and shown to the reader of every kind of source; what makes a store
one kind or another, and how its settings are worked out, is each reader's own."""

import logging
import re
from collections.abc import Mapping
from dataclasses import asdict, replace
from typing import Any

from listing_text.readers import condition_rules

from collector.clock import Clock
from collector.errors import OutOfTime, SourceUnavailable
from collector.polite import TimedPages, origin_of
from collector.ports import Fact
from collector.sites import Sites

log = logging.getLogger(__name__)


class NotAPage(Exception):
    """What was asked to be inspected is not the address of a page."""


def counted(count: float, unit: str) -> str:
    """A number of things, in words: "1 request", "2.5 seconds"."""
    return f"{count:,g} {unit}{'' if count == 1 else 's'}"


def run_time(requests: int, seconds_apart: float) -> str:
    """How long a run making this many requests, this far apart, would take, said roughly."""
    seconds = requests * seconds_apart
    spans = ((60, "minute"), (3600, "hour"), (86400, "day"))
    # Minutes up to an hour, hours up to two days, days beyond.
    size, unit = spans[0] if seconds < 3600 else spans[1] if seconds < 2 * 86400 else spans[2]
    took = "under a minute" if seconds < 60 else f"about {counted(round(seconds / size), unit)}"
    return f"{took} ({counted(requests, 'request')}, {counted(seconds_apart, 'second')} apart)"


class Inspector:
    def __init__(self, sites: Sites, clock: Clock, time_limit: float, run_delay: float) -> None:
        """time_limit: the seconds an inspection may read a store for before it gives up.
        run_delay: the least time a run leaves between two requests to a store."""
        self.sites, self.clock, self.time_limit = sites, clock, time_limit
        self.run_delay = run_delay

    def inspect(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """The sources that would read the page at request["url"], those that read the page's
        own product first, each with its settings, why they were chosen, and the first offer they read ("found");
        that none reads a drive from it ("nothing"); or why it could not be read ("failed")."""
        if "url" not in request:
            raise NotAPage("missing url")
        url = str(request["url"])
        if not re.match(r"https?://[^\s/]+", url):
            raise NotAPage("url is not a page's address")
        base = origin_of(url)
        answer: dict[str, Any] = {"base_url": base, "reason": None, "candidates": [], "notes": []}
        candidates: list[dict[str, Any]] = []
        try:
            conditions = condition_rules(
                (rule["pattern"], rule["condition"]) for rule in request.get("conditions", [])
            )
            visited = self.sites.visit(
                key="inspect",
                base_url=base,
                transport=request.get("transport", "direct"),
                conditions=conditions,
            )
            site = replace(visited, http=TimedPages(visited.http, self.clock, self.time_limit))
            page = site.http.get(url, min_delay=site.store.min_delay).text
            # A run waits what the store asks between requests, and never less than its own floor.
            apart = max(site.http.crawl_delay(base), self.run_delay)
            for kind, reader in self.sites.readers.items():
                found = reader.inspect(url, page, site)
                answer["notes"] += found.notes
                candidates += [
                    {
                        "linked": reading.linked,
                        "kind": kind,
                        "settings": reading.settings,
                        "evidence": reading.evidence,
                        "offers": len(reading.offers),
                        "offer": reading.offers[0].fields(),
                        "summary": [
                            asdict(fact)
                            for fact in (
                                *reading.summary,
                                *(
                                    [Fact("Time for a run", run_time(reading.requests, apart))]
                                    if reading.requests is not None
                                    else []
                                ),
                            )
                        ],
                    }
                    for reading in found.readings
                ]
        except (SourceUnavailable, OutOfTime) as error:
            log.info("inspect_failed", extra={"url": url, "error": str(error)})
            return {**answer, "status": "failed", "reason": str(error)}
        log.info("inspect_read", extra={"url": url, "candidates": len(candidates)})
        # Reading the linked product shows the settings fit the page. How many offers were read
        # does not compare across kinds (a collection's page against one product's), so beyond
        # that the kinds keep their order, and one kind's ways go by how much each read.
        kinds = list(self.sites.readers)
        candidates.sort(
            key=lambda candidate: (
                not candidate.pop("linked"),
                kinds.index(candidate["kind"]),
                -candidate["offers"],
            )
        )
        return {**answer, "status": "found" if candidates else "nothing", "candidates": candidates}
