"""Previewing a source: reading just enough of a store to show one offer, and keeping nothing.
It is how a source's settings are tried before the collector ever runs it."""

import logging
import re
from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from listing_text.readers import condition_rules

from collector.clock import Clock
from collector.errors import OutOfTime, SourceUnavailable
from collector.polite import TimedPages, same_site
from collector.ports import ReadsOnePage
from collector.sites import Sites

log = logging.getLogger(__name__)
# What a source to preview must say; its key, transport and condition rules have defaults.
REQUIRED = ("kind", "base_url", "settings")


class NotASource(Exception):
    """What was asked to be previewed does not describe a source."""


class Previewer:
    def __init__(self, sites: Sites, clock: Clock, time_limit: float) -> None:
        """time_limit: the seconds a preview may read a store for before it gives up."""
        self.sites, self.clock, self.time_limit = sites, clock, time_limit

    def preview(self, source: Mapping[str, Any]) -> dict[str, Any]:
        """The first offer the source reads ("found"), that it read none ("nothing"), or why
        it could not be read ("failed"), which includes running out of time; and notes on what
        was read. With a page_url, only that page of the store is read."""
        missing = next((name for name in REQUIRED if name not in source), None)
        if missing is not None:
            raise NotASource(f"missing {missing}")
        key = source.get("key", "preview")
        page = source.get("page_url") or None
        notes: list[str] = []
        try:
            if page and not same_site(page, source["base_url"]):
                raise SourceUnavailable("settings: the page to test is not on this store")
            conditions = condition_rules(
                (rule["pattern"], rule["condition"]) for rule in source.get("conditions", [])
            )
            reader, site = self.sites.open(
                key=key,
                kind=source["kind"],
                base_url=source["base_url"],
                transport=source.get("transport", "direct"),
                settings=source["settings"],
                conditions=conditions,
            )
            timed = replace(site, http=TimedPages(site.http, self.clock, self.time_limit))
            if page is None:
                found = reader.sample(timed, notes.append)
            elif isinstance(reader, ReadsOnePage):
                found = reader.page_offers(page, timed, notes.append)
            else:
                raise SourceUnavailable("settings: this kind of store cannot be tested on one page")
            offer = next(iter(found), None)
        except (SourceUnavailable, OutOfTime, re.error) as error:
            log.info("preview_failed", extra={"source": key, "error": str(error)})
            return {"status": "failed", "reason": str(error), "offer": None, "notes": notes}
        log.info("preview_read", extra={"source": key, "found": offer is not None})
        if offer is None:
            return {"status": "nothing", "reason": None, "offer": None, "notes": notes}
        return {"status": "found", "reason": None, "offer": offer.fields(), "notes": notes}
