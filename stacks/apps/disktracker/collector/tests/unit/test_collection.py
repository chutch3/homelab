import logging
from collections.abc import Callable, Iterator, Mapping
from typing import Any

import httpx
import pytest

from collector.collection import PROGRESS_EVERY, PROGRESS_SECONDS, Collector, stale_offers
from collector.errors import DisktrackerUnavailable, SourceUnavailable
from collector.models import RunSummary, ScrapedOffer, Store
from collector.pacer import Pacer
from collector.polite import PoliteHttp
from collector.ports import Site
from collector.sites import Sites
from tests.builders import CONDITION_RULES, listing, source_view
from tests.fakes import FakeClock, FakeDisktracker, FakeReader, offer

STORE = "https://store.test/"
# The source every run here collects: a Shopify store, read by the fake reader.
SOURCE = source_view("store")
MakeCollector = Callable[[FakeReader, FakeDisktracker], Collector]


def polite() -> PoliteHttp:
    clock = FakeClock()
    return PoliteHttp(httpx.Client(), Pacer(clock), clock)


TRANSPORTS = {"direct": polite(), "browser": polite()}


def test_only_in_stock_direct_offers_not_recorded_this_run_are_rechecked() -> None:
    missing = listing(f"{STORE}missing")
    elsewhere = listing("https://elsewhere.test/drive")
    recorded = listing(f"{STORE}moved-to-a-tray-listing")
    listings = [
        missing,
        recorded,
        listing(f"{STORE}known-sold-out", in_stock=False),
        listing(f"{STORE}marketplace", seller="Some shop"),
        listing(None),
        elsewhere,
    ]
    # Which of them are on the store's own product pages is the reader's to say.
    assert stale_offers(listings, {recorded.id}) == [missing, elsewhere]


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def subject(clock: FakeClock) -> MakeCollector:
    def make(reader: FakeReader, disktracker: FakeDisktracker) -> Collector:
        sites = Sites(readers={"shopify": reader}, transports=TRANSPORTS, min_delay=2)
        return Collector(disktracker=disktracker, sites=sites, clock=clock)

    return make


class TestCollector:
    def test_each_offer_is_posted_as_soon_as_it_is_read(self, subject: MakeCollector) -> None:
        journal: list[str] = []
        source = FakeReader([offer(f"{STORE}a"), offer(f"{STORE}b")], journal=journal)

        subject(source, FakeDisktracker(journal=journal)).collect(SOURCE, ())

        assert journal == [f"read {STORE}a", f"post {STORE}a", f"read {STORE}b", f"post {STORE}b"]

    def test_every_post_carries_the_time_the_run_started(
        self, subject: MakeCollector, clock: FakeClock
    ) -> None:
        disktracker = FakeDisktracker()

        subject(FakeReader([offer(f"{STORE}a"), offer(f"{STORE}b")]), disktracker).collect(
            SOURCE, ()
        )

        assert [observed_at for _, observed_at in disktracker.posted] == [clock.current] * 2

    def test_a_run_is_logged_from_start_to_its_tally(
        self, subject: MakeCollector, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        source = FakeReader([offer(f"{STORE}a"), offer(f"{STORE}b"), offer(f"{STORE}c")])

        summary = subject(
            source, FakeDisktracker(statuses=["recorded", "queued", "failed"])
        ).collect(SOURCE, ())

        assert summary == RunSummary(
            source="store", completed=True, seen=3, recorded=1, queued=1, failed=1
        )
        assert [(record.message, record.levelname) for record in caplog.records] == [
            ("run_started", "INFO"),
            ("run_complete", "INFO"),
        ]
        assert caplog.records[-1].__dict__["failed"] == 1

    def test_progress_is_logged_every_so_many_offers(
        self, subject: MakeCollector, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        source = FakeReader([offer(f"{STORE}{index}") for index in range(PROGRESS_EVERY * 2 + 1)])

        subject(source, FakeDisktracker()).collect(SOURCE, ())

        progress = [record.__dict__ for record in caplog.records if record.message == "progress"]
        assert [entry["seen"] for entry in progress] == [PROGRESS_EVERY, PROGRESS_EVERY * 2]

    def test_a_run_says_it_has_started_and_then_how_far_it_has_got_every_so_often(
        self, subject: MakeCollector, clock: FakeClock
    ) -> None:
        # Each post takes a third of the time between two reports.
        disktracker = FakeDisktracker(
            statuses=["recorded", "queued", "recorded", "failed"],
            on_post=lambda: clock.advance(PROGRESS_SECONDS / 3),
        )
        source = FakeReader([offer(f"{STORE}{index}") for index in range(4)])

        subject(source, disktracker).collect(SOURCE, ())

        counts = {"seen": 0, "recorded": 0, "queued": 0, "ignored": 0, "failed": 0}
        assert disktracker.progress == [
            ("store", clock.current, counts),
            ("store", clock.current, {**counts, "seen": 3, "recorded": 2, "queued": 1}),
        ]

    def test_a_run_told_to_stop_ends_there_and_is_reported_as_stopped_not_failed(
        self, subject: MakeCollector, clock: FakeClock, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        journal: list[str] = []
        # Told to stop the second time it says how far it has got: after its first offer.
        disktracker = FakeDisktracker(
            journal=journal,
            stop_from=2,
            listings=[listing(f"{STORE}gone")],
            on_post=lambda: clock.advance(PROGRESS_SECONDS),
        )
        source = FakeReader([offer(f"{STORE}a"), offer(f"{STORE}b")], journal=journal)

        summary = subject(source, disktracker).collect(SOURCE, ())

        assert summary == RunSummary(
            source="store", completed=False, stopped=True, seen=1, recorded=1
        )
        # Nothing more is read, and what the store no longer lists is not rechecked.
        assert journal == [f"read {STORE}a", f"post {STORE}a"]
        assert disktracker.asked_for == []
        assert [report[0] for report in disktracker.reports] == [summary]
        assert [(record.message, record.levelname) for record in caplog.records] == [
            ("run_started", "INFO"),
            ("run_stopped", "INFO"),
        ]

    def test_a_run_asked_to_stop_before_it_starts_reads_nothing(
        self, subject: MakeCollector
    ) -> None:
        source = FakeReader([offer(f"{STORE}a")])

        summary = subject(source, FakeDisktracker(stop_from=1)).collect(SOURCE, ())

        assert (summary.stopped, summary.seen, source.sites) == (True, 0, [])

    def test_progress_disktracker_cannot_take_does_not_stop_the_run(
        self, subject: MakeCollector
    ) -> None:
        disktracker = FakeDisktracker(progressing=DisktrackerUnavailable("progress: HTTP 503"))

        summary = subject(FakeReader([offer(f"{STORE}a")]), disktracker).collect(SOURCE, ())

        assert (summary.completed, summary.seen) == (True, 1)

    def test_a_store_that_cannot_be_read_fails_the_run(
        self, subject: MakeCollector, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        disktracker = FakeDisktracker()

        summary = subject(FakeReader(unavailable="store is down"), disktracker).collect(SOURCE, ())

        assert summary == RunSummary(source="store", completed=False)
        assert disktracker.posted == []
        failed = caplog.records[-1]
        assert (failed.message, failed.levelname, failed.__dict__["error"]) == (
            "run_failed",
            "ERROR",
            "store is down",
        )

    def test_a_store_that_fails_partway_reports_what_was_already_posted(
        self, subject: MakeCollector, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        source = FakeReader([offer(f"{STORE}a")], unavailable="page 2 is down")
        disktracker = FakeDisktracker()

        summary = subject(source, disktracker).collect(SOURCE, ())

        assert summary == RunSummary(source="store", completed=False, seen=1, recorded=1)
        assert len(disktracker.posted) == 1
        assert disktracker.asked_for == []
        failed = caplog.records[-1].__dict__
        assert (failed["seen"], failed["recorded"], failed["error"]) == (1, 1, "page 2 is down")

    def test_offers_that_left_the_store_are_rechecked_and_reposted(
        self, subject: MakeCollector
    ) -> None:
        gone = listing(f"{STORE}gone")
        sold_out = offer(f"{STORE}gone", item_price_cents=None, in_stock=False)
        source = FakeReader([offer(f"{STORE}listed")], rechecks={"gone": sold_out})
        disktracker = FakeDisktracker(listings=[gone])

        summary = subject(source, disktracker).collect(SOURCE, ())

        assert disktracker.asked_for == ["store"]
        assert [posted for posted, _ in disktracker.posted] == [offer(f"{STORE}listed"), sold_out]
        assert summary == RunSummary(
            source="store", completed=True, seen=1, recorded=1, rechecked=1
        )

    def test_an_offer_on_no_product_page_of_the_store_is_passed_over_and_the_rest_keep_their_order(
        self, subject: MakeCollector
    ) -> None:
        first, last = (offer(f"{STORE}{name}", in_stock=False) for name in ("first", "last"))
        source = FakeReader(rechecks={"first": first, "last": last})
        known = [
            listing(f"{STORE}first"),
            listing("https://elsewhere.test/drive"),
            listing(f"{STORE}last"),
        ]
        disktracker = FakeDisktracker(listings=known)

        summary = subject(source, disktracker).collect(SOURCE, ())

        assert [posted for posted, _ in disktracker.posted] == [first, last]
        assert summary == RunSummary(source="store", completed=True, rechecked=2)

    def test_a_recheck_disktracker_will_not_take_counts_as_a_failed_recheck(
        self, subject: MakeCollector
    ) -> None:
        source = FakeReader(rechecks={"gone": offer(f"{STORE}gone", in_stock=False)})
        disktracker = FakeDisktracker(statuses=["failed"], listings=[listing(f"{STORE}gone")])

        summary = subject(source, disktracker).collect(SOURCE, ())

        assert summary == RunSummary(source="store", completed=True, rechecked=1, recheck_failed=1)

    def test_a_recheck_that_fails_is_counted_and_logged_as_a_warning(
        self, subject: MakeCollector, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        source = FakeReader(rechecks={"gone": SourceUnavailable("page broke")})
        disktracker = FakeDisktracker(listings=[listing(f"{STORE}gone")])

        summary = subject(source, disktracker).collect(SOURCE, ())

        assert summary == RunSummary(source="store", completed=True, rechecked=1, recheck_failed=1)
        warning = next(record for record in caplog.records if record.message == "recheck_failed")
        assert (warning.levelname, warning.__dict__["url"], warning.__dict__["error"]) == (
            "WARNING",
            f"{STORE}gone",
            "page broke",
        )

    def test_listings_disktracker_cannot_give_skip_rechecks_but_the_run_completes(
        self, subject: MakeCollector, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        disktracker = FakeDisktracker(listings=DisktrackerUnavailable("listings: HTTP 503"))

        summary = subject(FakeReader([offer(f"{STORE}a")]), disktracker).collect(SOURCE, ())

        assert summary == RunSummary(source="store", completed=True, seen=1, recorded=1)
        assert [(record.message, record.levelname) for record in caplog.records][1] == (
            "recheck_failed",
            "WARNING",
        )

    def test_every_run_reports_its_summary_and_when_it_ran(
        self, subject: MakeCollector, clock: FakeClock
    ) -> None:
        disktracker = FakeDisktracker()

        completed = subject(FakeReader([offer(f"{STORE}a")]), disktracker).collect(SOURCE, ())
        failed = subject(FakeReader(unavailable="down"), disktracker).collect(SOURCE, ())

        assert disktracker.reports == [
            (completed, clock.current, clock.current),
            (failed, clock.current, clock.current),
        ]

    def test_a_source_is_read_through_its_transport_as_its_store_with_its_settings(
        self, subject: MakeCollector
    ) -> None:
        reader = FakeReader()
        collector = subject(reader, FakeDisktracker())

        collector.collect(
            source_view("store", settings={"collections": ["drives"]}), CONDITION_RULES
        )
        collector.collect(source_view("store", transport="browser"), ())

        assert reader.sites == [
            Site(
                TRANSPORTS["direct"],
                Store("store", "https://store.test", 2, CONDITION_RULES),
                {"collections": ["drives"]},
            ),
            Site(TRANSPORTS["browser"], Store("store", "https://store.test", 2, ()), {}),
        ]

    @pytest.mark.parametrize(
        ("source", "reason"),
        [
            (source_view(settings={"missing": "collections"}), "settings: missing collections"),
            (source_view(settings={"unreadable": "bad pattern"}), "settings: bad pattern"),
            (source_view(kind="manual"), "settings: a manual source is not collected"),
        ],
        ids=["a setting left out", "a setting that cannot be read", "a store entered by hand"],
    )
    def test_a_source_that_cannot_be_read_as_configured_fails_its_run_and_is_reported(
        self,
        subject: MakeCollector,
        clock: FakeClock,
        caplog: pytest.LogCaptureFixture,
        source: Any,
        reason: str,
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        reader, disktracker = FakeReader([offer(f"{STORE}a")]), FakeDisktracker()

        summary = subject(reader, disktracker).collect(source, ())

        assert summary == RunSummary(source="store", completed=False)
        assert (reader.sites, disktracker.posted) == ([], [])
        assert disktracker.reports == [(summary, clock.current, clock.current)]
        failed = caplog.records[-1]
        assert (failed.message, failed.__dict__["error"]) == ("run_failed", reason)

    def test_a_run_that_crashes_is_reported_as_failed_so_it_is_not_due_again_at_once(
        self, subject: MakeCollector, clock: FakeClock
    ) -> None:
        class Crashing(FakeReader):
            def offers(self, site: Site[Mapping[str, Any]]) -> Iterator[ScrapedOffer]:
                raise KeyError("variants")

        disktracker = FakeDisktracker()

        with pytest.raises(KeyError):
            subject(Crashing(), disktracker).collect(SOURCE, ())

        assert disktracker.reports == [
            (RunSummary(source="store", completed=False), clock.current, clock.current)
        ]

    def test_a_report_disktracker_will_not_take_is_logged_and_the_run_still_counts(
        self, subject: MakeCollector, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        disktracker = FakeDisktracker(reporting=DisktrackerUnavailable("runs: HTTP 503"))

        summary = subject(FakeReader([offer(f"{STORE}a")]), disktracker).collect(SOURCE, ())

        assert summary == RunSummary(source="store", completed=True, seen=1, recorded=1)
        warning = caplog.records[-1]
        assert (warning.message, warning.levelname, warning.__dict__["error"]) == (
            "run_report_failed",
            "WARNING",
            "runs: HTTP 503",
        )
