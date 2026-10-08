"""Collecting one source: read its offers and post each to disktracker as it comes, then
recheck the offers disktracker still has in stock that this run did not record."""

import logging
from collections import Counter
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from listing_text.readers import ConditionRules

from collector.clock import Clock
from collector.errors import DisktrackerUnavailable, SourceUnavailable
from collector.models import RunSummary, ScrapedOffer
from collector.ports import Disktracker, Rechecked
from collector.sites import Sites
from disktracker_api.models import ListingSummary, SourceView

log = logging.getLogger(__name__)
PROGRESS_EVERY = 50
# How often, at most, a run tells disktracker how far it has got, and learns whether to stop.
PROGRESS_SECONDS = 15.0
STATUSES = ("recorded", "queued", "ignored", "failed")


def stale_offers(listings: list[ListingSummary], recorded: set[UUID]) -> list[ListingSummary]:
    """The store's direct offers disktracker still has in stock that this run did not record.
    Offers are matched by id, not URL: one recorded from another listing of the same drive
    keeps the URL it was first saved with."""
    return [
        listing
        for listing in listings
        if listing.url
        and listing.seller == ""
        and listing.latest.in_stock
        and listing.id not in recorded
    ]


class Collector:
    """Collects a source: reads its offers with the reader for its kind, fetching its pages
    through its transport, and posts each as it comes; then rechecks what the store no longer
    lists; then reports the run. As it goes it tells disktracker how far it has got, and ends
    there, with what it has posted kept, when disktracker says it was asked to stop. A source
    that cannot be read as configured fails its run with the reason, and is reported like any
    other."""

    def __init__(self, disktracker: Disktracker, sites: Sites, clock: Clock) -> None:
        self.disktracker, self.sites, self.clock = disktracker, sites, clock

    def collect(self, source: SourceView, conditions: ConditionRules) -> RunSummary:
        """The run's summary, reported to disktracker. A run that crashes is reported as failed
        before the crash goes on, so its source is not due again until its schedule fires."""
        started = self.clock.now()
        try:
            summary = self._collect(source, conditions, started)
        except Exception:
            self._report(RunSummary(source=source.key, completed=False), started)
            raise
        self._report(summary, started)
        return summary

    def _report(self, summary: RunSummary, started: datetime) -> None:
        try:
            self.disktracker.report_run(summary, started, self.clock.now())
        except DisktrackerUnavailable as error:
            log.warning("run_report_failed", extra={"source": summary.source, "error": str(error)})

    def _collect(self, source: SourceView, conditions: ConditionRules, now: datetime) -> RunSummary:
        name = source.key
        log.info("run_started", extra={"source": name})
        tally: Counter[str] = Counter()
        recorded: set[UUID] = set()
        # The URLs of offers recorded this run, whatever listing took them.
        recorded_urls: set[str] = set()
        seen = 0

        def posted() -> dict[str, int]:
            return {"seen": seen, **{status: tally[status] for status in STATUSES}}

        def stopped() -> RunSummary:
            log.info("run_stopped", extra={"source": name, **posted()})
            return RunSummary(source=name, completed=False, stopped=True, **posted())

        told = self.clock.monotonic()
        if self._asked_to_stop(name, now, posted()):
            return stopped()
        try:
            reader, site = self.sites.open(
                key=name,
                kind=source.kind,
                base_url=source.base_url,
                transport=source.transport,
                settings=source.settings.to_dict(),
                conditions=conditions,
            )
            for offer in reader.offers(site):
                result = self.disktracker.post_scraped(offer, observed_at=now)
                seen += 1
                tally[result.status] += 1
                if result.listing_id:
                    recorded.add(result.listing_id)
                    recorded_urls.add(offer.url)
                if seen % PROGRESS_EVERY == 0:
                    log.info("progress", extra={"source": name, **posted()})
                if self.clock.monotonic() - told >= PROGRESS_SECONDS:
                    told = self.clock.monotonic()
                    if self._asked_to_stop(name, now, posted()):
                        return stopped()
        except SourceUnavailable as error:
            log.error("run_failed", extra={"source": name, "error": str(error), **posted()})
            return RunSummary(source=name, completed=False, stopped=False, **posted())
        stale = self._stale(name, recorded)
        # An offer recorded this run under another listing (read with another condition, say)
        # has left this one, and its page is not fetched again; the rest are checked on their
        # pages by the reader, which gives them back in the order they were given.
        retired = [listing for listing in stale if listing.url in recorded_urls]
        checked = iter(reader.recheck([one for one in stale if one not in retired], site))
        awaited = next(checked, None)
        rechecked = recheck_failed = 0
        for listing in stale:
            if listing in retired:
                done = self._retire(name, listing, now)
            elif awaited is not None and awaited.listing is listing:
                done = self._rechecked(name, awaited, now)
                awaited = next(checked, None)
            else:
                # Not on a product page of this store: the reader passed it over.
                continue
            rechecked += 1
            recheck_failed += not done
        summary = RunSummary(
            source=name,
            completed=True,
            stopped=False,
            **posted(),
            rechecked=rechecked,
            recheck_failed=recheck_failed,
        )
        log.info(
            "run_complete",
            extra={key: value for key, value in asdict(summary).items() if key != "completed"},
        )
        return summary

    def _asked_to_stop(self, name: str, started: datetime, counts: dict[str, int]) -> bool:
        """Tell disktracker how far the run has got. A disktracker that cannot be told has not
        asked for anything: the run goes on."""
        try:
            return self.disktracker.report_progress(name, started, counts)
        except DisktrackerUnavailable as error:
            log.debug("progress_report_failed", extra={"source": name, "error": str(error)})
            return False

    def _retire(self, name: str, listing: ListingSummary, now: datetime) -> bool:
        """An offer recorded this run under another listing (read with another condition, say)
        has left this one: it is out of stock here, with no new price, and its page is not
        fetched again."""
        offer = ScrapedOffer.recheck(
            listing, source=name, item_price_cents=None, in_stock=False, shipping_cents=None
        )
        return self.disktracker.post_scraped(offer, observed_at=now).status != "failed"

    def _rechecked(self, name: str, checked: Rechecked, now: datetime) -> bool:
        """Whether the offer was read from its page and disktracker took it."""
        if checked.offer is None:
            log.warning(
                "recheck_failed",
                extra={"source": name, "url": checked.listing.url, "error": checked.error},
            )
            return False
        return self.disktracker.post_scraped(checked.offer, observed_at=now).status != "failed"

    def _stale(self, name: str, recorded: set[UUID]) -> list[ListingSummary]:
        try:
            known = self.disktracker.listings(store=name)
        except DisktrackerUnavailable as error:
            log.warning("recheck_failed", extra={"source": name, "error": str(error)})
            return []
        return stale_offers(known, recorded)
