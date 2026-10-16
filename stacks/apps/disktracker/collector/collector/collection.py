"""Collecting one source: read its offers and post each to disktracker as it comes, then
recheck the offers disktracker still has in stock that this run did not record."""

import logging
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from uuid import UUID

from listing_text.readers import ConditionRules

from collector.clock import Clock
from collector.errors import DisktrackerUnavailable, SourceUnavailable
from collector.models import RunSummary, ScrapedOffer, SourceView
from collector.ports import Disktracker, Rechecked
from collector.sites import Sites
from disktracker_api.models import OfferSummary

log = logging.getLogger(__name__)
PROGRESS_EVERY = 50
# How often, at most, a run tells disktracker how far it has got, and learns whether to stop.
PROGRESS_SECONDS = 15.0
STATUSES = ("recorded", "queued", "ignored", "failed")


def stale_offers(known: list[OfferSummary], recorded: set[UUID]) -> list[OfferSummary]:
    """The store's direct offers disktracker still has in stock that this run did not record.
    Offers are matched by id, not URL: one recorded from another listing of the same drive
    keeps the URL it was first saved with."""
    return [
        offer
        for offer in known
        if offer.url and offer.seller == "" and offer.latest.in_stock and offer.id not in recorded
    ]


class Collector:
    """Collects a source: reads its offers with the reader for its kind, fetching its pages
    through its transport, and posts each as it comes; then rechecks what the store no longer
    lists; then reports the run. As it goes it tells disktracker how far it has got, and ends
    there, with what it has posted kept, when disktracker says it was asked to stop. A source
    that cannot be read as configured fails its run with the reason, and is reported like any
    other."""

    def __init__(
        self,
        disktracker: Disktracker,
        sites: Sites,
        clock: Clock,
        new_id: Callable[[], UUID],
    ) -> None:
        self.disktracker, self.sites, self.clock, self.new_id = disktracker, sites, clock, new_id

    def collect(self, source: SourceView, conditions: ConditionRules) -> RunSummary:
        """The run's summary. The run is registered with disktracker as it starts and its end
        is reported under the same id; one that crashes is reported as failed before the crash
        goes on, so its source is not due again until its schedule fires. A run disktracker
        cannot register is still collected, but nothing more is said of it."""
        started = self.clock.now()
        run = self._register(source.key, started)
        if run is None:
            # Nothing could say how far it got, end it or stop it: the source waits for the
            # next time it is due.
            return RunSummary(source=source.key, completed=False)
        try:
            summary = self._collect(source, conditions, started, run)
        except Exception as error:
            crashed = f"The collector crashed: {error!r}"
            self._report(run, RunSummary(source=source.key, completed=False, reason=crashed))
            raise
        self._report(run, summary)
        return summary

    def _register(self, name: str, started: datetime) -> UUID | None:
        run_id = self.new_id()
        try:
            self.disktracker.start_run(run_id, name, started)
        except DisktrackerUnavailable as error:
            log.warning("run_start_failed", extra={"source": name, "error": str(error)})
            return None
        return run_id

    def _report(self, run: UUID, summary: RunSummary) -> None:
        try:
            self.disktracker.finish_run(run, summary, self.clock.now())
        except DisktrackerUnavailable as error:
            log.warning("run_report_failed", extra={"source": summary.source, "error": str(error)})

    def _collect(
        self, source: SourceView, conditions: ConditionRules, now: datetime, run: UUID
    ) -> RunSummary:
        name = source.key
        log.info("run_started", extra={"source": name})
        tally: Counter[str] = Counter()
        recorded: set[UUID] = set()
        # The URLs of offers recorded this run, whatever offer took them.
        recorded_urls: set[str] = set()
        seen = rechecked = recheck_failed = 0

        def posted() -> dict[str, int]:
            return {"seen": seen, **{status: tally[status] for status in STATUSES}}

        def done() -> dict[str, int]:
            """What the run has done: posted, and rechecked once it rechecks."""
            if not rechecked:
                return posted()
            return {**posted(), "rechecked": rechecked, "recheck_failed": recheck_failed}

        def stopped() -> RunSummary:
            log.info("run_stopped", extra={"source": name, **done()})
            # Asked to stop, it has no failure to say why of.
            return RunSummary(source=name, completed=False, stopped=True, reason=None, **done())

        told = self.clock.monotonic()
        if self._asked_to_stop(name, run, posted()):
            return stopped()
        try:
            reader, site = self.sites.open(
                key=name,
                kind=source.kind,
                base_url=source.base_url,
                transport=source.transport,
                settings=source.settings.to_dict(),
                conditions=conditions,
                obey_robots=source.obey_robots,
            )
            for offer in reader.offers(site):
                result = self.disktracker.post_scraped(offer, observed_at=now)
                seen += 1
                tally[result.status] += 1
                if result.offer_id:
                    recorded.add(result.offer_id)
                    recorded_urls.add(offer.url)
                if seen % PROGRESS_EVERY == 0:
                    log.info("progress", extra={"source": name, **posted()})
                if self.clock.monotonic() - told >= PROGRESS_SECONDS:
                    told = self.clock.monotonic()
                    if self._asked_to_stop(name, run, posted()):
                        return stopped()
        except SourceUnavailable as error:
            log.error("run_failed", extra={"source": name, "error": str(error), **posted()})
            # Its first line: what went wrong, without any advice after it.
            reason = str(error).splitlines()[0] if str(error) else None
            return RunSummary(
                source=name, completed=False, stopped=False, reason=reason, **posted()
            )
        stale = self._stale(name, recorded)
        # An offer recorded this run as another offer (read with another condition, say)
        # has left this one, and its page is not fetched again; the rest are checked on their
        # pages by the reader, which gives them back in the order they were given.
        retired = [offer for offer in stale if offer.url in recorded_urls]
        checked = iter(reader.recheck([one for one in stale if one not in retired], site))
        awaited = next(checked, None)
        for known in stale:
            if known in retired:
                checked_well = self._retire(name, known, now)
            elif awaited is not None and awaited.known is known:
                checked_well = self._rechecked(name, awaited, now)
                awaited = next(checked, None)
            else:
                # Not on a product page of this store: the reader passed it over.
                continue
            rechecked += 1
            recheck_failed += not checked_well
            if self.clock.monotonic() - told >= PROGRESS_SECONDS:
                told = self.clock.monotonic()
                if self._asked_to_stop(name, run, done()):
                    return stopped()
        summary = RunSummary(
            source=name,
            completed=True,
            stopped=False,
            reason=None,
            **posted(),
            rechecked=rechecked,
            recheck_failed=recheck_failed,
        )
        log.info(
            "run_complete",
            # Completed, it has no reason to give.
            extra={k: v for k, v in asdict(summary).items() if k not in ("completed", "reason")},
        )
        return summary

    def _asked_to_stop(self, name: str, run: UUID, counts: dict[str, int]) -> bool:
        """Say the collector is alive with this run, and how far the run has got. A disktracker
        that cannot be told has not asked for anything: the run goes on."""
        try:
            self.disktracker.heartbeat([run])
        except DisktrackerUnavailable as error:
            log.debug("heartbeat_failed", extra={"source": name, "error": str(error)})
        try:
            return self.disktracker.report_progress(run, counts)
        except DisktrackerUnavailable as error:
            log.debug("progress_report_failed", extra={"source": name, "error": str(error)})
            return False

    def _retire(self, name: str, known: OfferSummary, now: datetime) -> bool:
        """An offer recorded this run as another offer (read with another condition, say)
        has left this one: it is out of stock here, with no new price, and its page is not
        fetched again."""
        offer = ScrapedOffer.recheck(
            known, source=name, item_price_cents=None, in_stock=False, shipping_cents=None
        )
        return self.disktracker.post_scraped(offer, observed_at=now).status != "failed"

    def _rechecked(self, name: str, checked: Rechecked, now: datetime) -> bool:
        """Whether the offer was read from its page and disktracker took it."""
        if checked.offer is None:
            log.warning(
                "recheck_failed",
                extra={"source": name, "url": checked.known.url, "error": checked.error},
            )
            return False
        return self.disktracker.post_scraped(checked.offer, observed_at=now).status != "failed"

    def _stale(self, name: str, recorded: set[UUID]) -> list[OfferSummary]:
        try:
            known = self.disktracker.known_offers(store=name)
        except DisktrackerUnavailable as error:
            log.warning("recheck_failed", extra={"source": name, "error": str(error)})
            return []
        return stale_offers(known, recorded)
