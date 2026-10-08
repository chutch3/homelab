import json
import re
import signal
import subprocess
import time
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response

from tests.builders import listing_json
from tests.integration.harness import (
    ALLOW_ALL,
    RECORDED,
    ROOT,
    base_of,
    environment,
    events,
    know_listings,
    log_lines,
    posts,
    progress_reports,
    rechecks,
    record_everything,
    reply_in_turn,
    run,
    run_reports,
    scraped,
    serve_condition_rules,
    serve_robots,
    source_json,
    start_loop,
)

PAGE = json.loads((ROOT / "tests/fixtures/serverpartdeals_page1.json").read_text())
TRAYS = json.loads((ROOT / "tests/fixtures/serverpartdeals_tray_variants.json").read_text())
PRODUCTS = "/collections/hard-drives/products.json"
SSDS = "/collections/solid-state-drives/products.json"
TEN_THOUSAND_DOLLARS = 1_000_000


def spd_source(serverpartdeals: HTTPServer, **fields: Any) -> dict[str, Any]:
    """ServerPartDeals as the collector's Shopify source, configured as disktracker seeds it."""
    settings = {
        "collections": ["hard-drives", "solid-state-drives"],
        "free_shipping": True,
    }
    return source_json(
        "serverpartdeals",
        "shopify",
        base_of(serverpartdeals),
        settings,
        **fields,
    )


def collector_env(serverpartdeals: HTTPServer, disktracker: HTTPServer) -> dict[str, str]:
    return environment(disktracker, spd_source(serverpartdeals))


def run_collector(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> subprocess.CompletedProcess[str]:
    return run(collector_env(serverpartdeals, disktracker))


def serve_feed(
    serverpartdeals: HTTPServer,
    products: list[dict[str, Any]],
    ssds: list[dict[str, Any]] | None = None,
    robots: str = ALLOW_ALL,
) -> None:
    """One page of hard drives and one of SSDs (none unless given), each followed by an empty
    page, under these robots.txt rules."""
    serve_robots(serverpartdeals, robots)
    for collection, listed in ((PRODUCTS, products), (SSDS, ssds or [])):
        serverpartdeals.expect_request(
            collection, query_string="limit=250&page=1"
        ).respond_with_json({"products": listed})
        serverpartdeals.expect_request(
            collection, query_string="limit=250&page=2"
        ).respond_with_json({"products": []})


def test_one_run_posts_every_serverpartdeals_offer_to_disktracker(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    reply_in_turn(
        disktracker,
        [
            (scraped("recorded", listing_id=UUID(int=1)), 201),
            (scraped("recorded", listing_id=UUID(int=2)), 201),
            (scraped("queued", unmatched_id=UUID(int=3)), 202),
        ],
    )
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    requests = posts(disktracker)
    posted = [json.loads(request.data) for request in requests]
    base = base_of(serverpartdeals)
    observed = {offer.pop("observed_at") for offer in posted}
    assert len(observed) == 1

    def offer(**fields: Any) -> dict[str, Any]:
        return {
            "source": "serverpartdeals",
            "seller": "",
            "shipping_cents": 0,
            "aliases": [],
            "brand": None,
            **fields,
        }

    assert posted == [
        offer(
            url=f"{base}/products/seagate-exos-x20-st18000nm003d-18tb",
            title=PAGE["products"][0]["title"],
            mpn="ST18000NM003D",
            brand="Seagate",
            condition="manufacturer_recertified",
            capacity_gb=18000,
            item_price_cents=51900,
            in_stock=True,
            specifications={
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sata",
                "intended_use": ["enterprise"],
            },
        ),
        offer(
            url=f"{base}/products/wd-ultrastar-hc550-wuh721818ale6l4",
            title=PAGE["products"][1]["title"],
            mpn="WUH721818ALE6L4",
            brand="Western Digital",
            condition="refurbished",
            capacity_gb=18000,
            item_price_cents=48900,
            in_stock=False,
            specifications={
                "media_type": "hdd",
                "form_factor": "3_5",
                "interface": "sata",
                "intended_use": ["enterprise"],
            },
        ),
        offer(
            url=f"{base}/products/intel-d3-s4510-960gb?variant=9003",
            title="Intel D3-S4510 960GB SATA 2.5in SSD (Bulk)",
            mpn=None,
            brand="Intel",
            condition="used",
            capacity_gb=960,
            item_price_cents=7499,
            in_stock=True,
            specifications={"media_type": "ssd", "form_factor": "2_5", "interface": "sata"},
        ),
    ]
    keys = [UUID(request.headers["Idempotency-Key"]) for request in requests]
    assert len(set(keys)) == 3
    assert events(result.stdout)[-1] == {
        "event": "run_complete",
        "source": "serverpartdeals",
        "seen": 3,
        "recorded": 2,
        "queued": 1,
        "ignored": 0,
        "failed": 0,
        "rechecked": 0,
        "recheck_failed": 0,
        "stopped": False,
    }


def test_failing_or_rejected_posts_are_counted_and_the_run_carries_on(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    gateway_error = "<html><body>502 Bad Gateway</body></html>"
    reply_in_turn(
        disktracker,
        [
            (json.dumps({"detail": "busy"}), 503),
            (scraped("recorded", listing_id=UUID(int=1)), 201),
            (json.dumps({"detail": [{"loc": ["body", "url"], "msg": "bad", "type": "x"}]}), 422),
            (gateway_error, 502),
            (gateway_error, 502),
            (gateway_error, 502),
        ],
    )
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    keys = [request.headers["Idempotency-Key"] for request in posts(disktracker)]
    assert len(keys) == 6
    assert keys[0] == keys[1]
    assert len(set(keys[3:])) == 1
    base = base_of(serverpartdeals)
    assert [event for event in events(result.stdout) if event["event"] == "post_failed"] == [
        {
            "event": "post_failed",
            "url": f"{base}/products/wd-ultrastar-hc550-wuh721818ale6l4",
            "status": 422,
            "detail": [{"loc": ["body", "url"], "msg": "bad", "type": "x"}],
        },
        {
            "event": "post_failed",
            "url": f"{base}/products/intel-d3-s4510-960gb?variant=9003",
            "status": 502,
            "detail": gateway_error,
        },
    ]
    assert events(result.stdout)[-1] == {
        "event": "run_complete",
        "source": "serverpartdeals",
        "seen": 3,
        "recorded": 1,
        "queued": 0,
        "ignored": 0,
        "failed": 2,
        "rechecked": 0,
        "recheck_failed": 0,
        "stopped": False,
    }


def test_each_run_reports_what_it_did_and_when_to_disktracker(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    reply_in_turn(
        disktracker,
        [
            (scraped("recorded", RECORDED), 201),
            (scraped("queued"), 202),
            ('{"detail": "rejected"}', 409),
        ],
    )
    know_listings(disktracker, [])
    before = datetime.now(UTC)

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    [report] = run_reports(disktracker)
    started, finished = (
        datetime.fromisoformat(report.pop(key)) for key in ("started_at", "finished_at")
    )
    assert before <= started <= finished <= datetime.now(UTC)
    assert report == {
        "source": "serverpartdeals",
        "completed": True,
        "seen": 3,
        "recorded": 1,
        "queued": 1,
        "ignored": 0,
        "failed": 1,
        "rechecked": 0,
        "recheck_failed": 0,
        "stopped": False,
    }


def test_a_switched_off_source_asked_to_run_now_is_collected(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run(environment(disktracker, spd_source(serverpartdeals, enabled=False)))

    assert result.returncode == 0, result.stderr
    assert len(posts(disktracker)) == 3


def test_a_source_whose_settings_cannot_be_read_fails_its_run_and_the_others_still_run(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    record_everything(disktracker)
    know_listings(disktracker, [])
    # Saved without the collections a Shopify source reads.
    broken = source_json("oldmap", "shopify", "https://ghd.test", {})

    result = run(environment(disktracker, broken, spd_source(serverpartdeals)))

    assert result.returncode == 1
    assert len(posts(disktracker)) == 3
    [failed] = [event for event in events(result.stdout) if event["event"] == "run_failed"]
    assert (failed["source"], failed["error"]) == (
        "oldmap",
        "settings: missing collections",
    )
    assert [(report["source"], report["completed"]) for report in run_reports(disktracker)] == [
        ("oldmap", False),
        ("serverpartdeals", True),
    ]


def test_a_run_says_it_has_started_before_it_reads_the_store(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    [started] = progress_reports(disktracker)
    [report] = run_reports(disktracker)
    assert started == {
        "source": "serverpartdeals",
        "started_at": report["started_at"],
        "seen": 0,
        "recorded": 0,
        "queued": 0,
        "ignored": 0,
        "failed": 0,
    }
    paths = [request.path for request, _ in disktracker.log]
    assert paths.index("/api/collector-activity") < paths.index("/api/scraped")
    assert report["stopped"] is False


def test_a_run_disktracker_asks_to_stop_ends_there_and_is_reported_as_stopped(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    record_everything(disktracker)
    disktracker.expect_oneshot_request("/api/collector-activity", method="PUT").respond_with_json(
        {"stop": True}
    )

    result = run_collector(serverpartdeals, disktracker)

    # Stopped is not completed, so the round did not succeed.
    assert result.returncode == 1, result.stderr
    assert posts(disktracker) == []
    assert serverpartdeals.log == []
    [report] = run_reports(disktracker)
    assert (report["completed"], report["stopped"], report["seen"]) == (False, True, 0)
    assert {"event": "run_stopped", "source": "serverpartdeals", "seen": 0, "recorded": 0,
            "queued": 0, "ignored": 0, "failed": 0} in events(result.stdout)  # fmt: skip


@pytest.mark.parametrize(
    ("body", "status"), [("down", 503), ("{}", 200)], ids=["an error", "an answer it cannot read"]
)
def test_a_run_goes_on_when_disktracker_cannot_be_told_how_far_it_has_got(
    serverpartdeals: HTTPServer, disktracker: HTTPServer, body: str, status: int
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    record_everything(disktracker)
    know_listings(disktracker, [])
    disktracker.expect_oneshot_request("/api/collector-activity", method="PUT").respond_with_data(
        body, status=status, content_type="application/json"
    )

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    [report] = run_reports(disktracker)
    assert (report["completed"], report["stopped"], report["seen"]) == (True, False, 3)


def test_what_is_due_is_asked_again_after_each_run_so_a_store_asked_for_meanwhile_goes_next(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, [])
    know_listings(disktracker, [])
    know_listings(disktracker, [], store="asked")
    first = spd_source(serverpartdeals)
    asked = {**spd_source(serverpartdeals), "key": "asked", "name": "Asked"}
    # Asked is not due when the round starts; it is asked to run while the first store runs.
    answers = iter([[first], [asked], []])
    disktracker.expect_request("/api/sources/due", method="GET").respond_with_handler(
        lambda _request: Response(json.dumps(next(answers)), content_type="application/json")
    )
    serve_condition_rules(disktracker, [])

    result = run({
        **environment(disktracker), "DISKTRACKER_URL": base_of(disktracker),
    })  # fmt: skip

    assert result.returncode == 0, result.stderr
    assert [report["source"] for report in run_reports(disktracker)] == ["serverpartdeals", "asked"]


def test_a_run_with_nothing_due_collects_nothing_and_succeeds(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    result = run(environment(disktracker))

    assert result.returncode == 0, result.stderr
    assert serverpartdeals.log == []
    assert posts(disktracker) == []


def test_a_run_fails_when_disktracker_cannot_say_which_sources_to_collect(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    disktracker.expect_oneshot_request("/api/sources/due", method="GET").respond_with_data(
        "busy", status=503
    )

    result = run(collector_env(serverpartdeals, disktracker))

    assert result.returncode == 1
    assert serverpartdeals.log == []
    assert events(result.stdout)[-1] == {
        "event": "sources_unavailable",
        "error": "sources: HTTP 503",
    }


def test_a_run_fails_when_disktracker_answers_in_a_shape_the_collector_cannot_read(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    # An older disktracker, from before sources had a transport.
    older = {**spd_source(serverpartdeals)}
    del older["transport"]
    disktracker.expect_oneshot_request("/api/sources/due", method="GET").respond_with_json([older])

    result = run(collector_env(serverpartdeals, disktracker))

    assert result.returncode == 1
    assert result.stderr == ""
    assert serverpartdeals.log == []
    assert events(result.stdout)[-1] == {
        "event": "sources_unavailable",
        "error": "sources: the answer has no transport",
    }


def test_conditions_are_read_with_disktrackers_rules_the_first_match_winning(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    exos = PAGE["products"][0]
    renewed = {
        **exos,
        "id": 101,
        "handle": "renewed",
        "title": "Seagate Exos X20 ST18000NM003D 18TB (Renewed) Hard Drive",
        "tags": ["capacity:18TB", "condition:New"],
    }
    pre_owned = {
        **exos,
        "id": 102,
        "handle": "pre-owned",
        "title": "Seagate Exos X18 ST18000NM000J 18TB Pre-Owned Hard Drive",
        "tags": ["capacity:18TB"],
        "variants": [{**exos["variants"][0], "id": 1102, "sku": "ST18000NM000J_U"}],
    }
    serve_condition_rules(
        disktracker,
        [
            {"pattern": r"\bpre-?owned\b", "condition": "used"},
            {"pattern": r"\brenewed\b", "condition": "refurbished"},
            {"pattern": r"\bnew\b", "condition": "new"},
        ],
    )
    serve_feed(serverpartdeals, [renewed, pre_owned])
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    # The title's "Renewed" outranks the store's "New" tag: its rule comes first.
    assert [json.loads(request.data)["condition"] for request in posts(disktracker)] == [
        "refurbished",
        "used",
    ]


def test_an_offer_now_read_under_another_condition_leaves_its_old_listing_out_of_stock(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"][:1])
    url = f"{base_of(serverpartdeals)}/products/seagate-exos-x20-st18000nm003d-18tb"
    # Recorded as new before a condition rule read it right.
    old = listing_json(url, listing_id=UUID(int=9), mpn="ST18000NM003D", condition="new")
    know_listings(disktracker, [old])
    record_everything(disktracker)

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    assert not [request for request, _ in serverpartdeals.log if request.path.endswith(".js")]
    [superseded] = rechecks(disktracker)
    assert (superseded["url"], superseded["condition"], superseded["in_stock"]) == (
        url,
        "new",
        False,
    )
    assert superseded["item_price_cents"] is None
    assert events(result.stdout)[-1]["rechecked"] == 1


def test_a_run_fails_when_disktracker_cannot_give_its_condition_rules(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    disktracker.expect_oneshot_request("/api/condition-rules", method="GET").respond_with_data(
        "busy", status=503
    )

    result = run(collector_env(serverpartdeals, disktracker))

    assert result.returncode == 1
    assert serverpartdeals.log == []
    assert events(result.stdout)[-1] == {
        "event": "sources_unavailable",
        "error": "condition rules: HTTP 503",
    }


def test_a_run_fails_when_disktracker_is_unreachable_from_the_start(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    env = collector_env(serverpartdeals, disktracker)
    disktracker.stop()

    result = run(env)

    assert result.returncode == 1
    assert serverpartdeals.log == []
    assert events(result.stdout)[-1] == {
        "event": "sources_unavailable",
        "error": "[Errno 111] Connection refused",
    }


def test_an_unreachable_source_is_reported_and_nothing_is_posted(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request(PRODUCTS).respond_with_data("down", status=503)

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 1
    assert posts(disktracker) == []
    [report] = run_reports(disktracker)
    assert {key: value for key, value in report.items() if not key.endswith("_at")} == {
        "source": "serverpartdeals",
        "completed": False,
        "seen": 0,
        "recorded": 0,
        "queued": 0,
        "ignored": 0,
        "failed": 0,
        "rechecked": 0,
        "recheck_failed": 0,
        "stopped": False,
    }
    url = serverpartdeals.url_for(PRODUCTS) + "?limit=250&page=1"
    assert events(result.stdout) == [
        {"event": "run_started", "source": "serverpartdeals"},
        {
            "event": "run_failed",
            "source": "serverpartdeals",
            "seen": 0,
            "recorded": 0,
            "queued": 0,
            "ignored": 0,
            "failed": 0,
            "error": f"Server error '503 SERVICE UNAVAILABLE' for url '{url}'\n"
            "For more information check: https://developer.mozilla.org/en-US/docs/Web/HTTP/Status/503",
        },
    ]


def test_a_feed_that_is_not_json_is_reported_as_unavailable(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_robots(serverpartdeals)
    serverpartdeals.expect_request(PRODUCTS).respond_with_data(
        "<html>Checking your browser</html>", content_type="text/html"
    )

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 1
    assert posts(disktracker) == []
    started, failed = events(result.stdout)
    assert started == {"event": "run_started", "source": "serverpartdeals"}
    assert (failed["event"], failed["source"]) == ("run_failed", "serverpartdeals")
    assert failed["error"].startswith("Expecting value")


def test_tray_and_part_number_listings_of_one_drive_post_as_a_single_offer(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, TRAYS["products"])
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    posted = [json.loads(request.data) for request in posts(disktracker)]
    base = base_of(serverpartdeals)
    assert [(offer["url"], offer["condition"], offer["item_price_cents"]) for offer in posted] == [
        (
            f"{base}/products/dell-wd-ultrastar-hc550-wuh721816al5205-refurbished",
            "refurbished",
            49900,
        ),
        (f"{base}/products/dell-g14-0hnhwc-16tb-new", "new", 87900),
    ]
    assert {(offer["mpn"], tuple(offer["aliases"])) for offer in posted} == {
        ("WUH721816AL5205", ("0HNHWC",))
    }
    summary = events(result.stdout)[-1]
    assert (summary["seen"], summary["recorded"]) == (2, 2)


def test_a_wd_model_code_with_letters_is_still_read_as_the_maker_mpn(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    hc320 = {
        **PAGE["products"][0],
        "id": 320,
        "handle": "dell-hc320",
        "title": "Dell/Western Digital Ultrastar DC HC320 HUS728T8TAL5200 0B36416 8TB SAS",
        "variants": [{**PAGE["products"][0]["variants"][0], "sku": "044YFV_NOTRAY_SR"}],
    }
    # No title names Dell's part number, but most of the store's titles name their own SKU, so
    # its SKUs are part numbers: this one joins the drive as an alias.
    serve_feed(serverpartdeals, [*PAGE["products"], hc320])
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    [posted] = [
        json.loads(request.data)
        for request in posts(disktracker)
        if json.loads(request.data)["url"].endswith("/dell-hc320")
    ]
    assert (posted["mpn"], posted["aliases"]) == ("HUS728T8TAL5200", ["044YFV"])


def test_without_run_once_it_asks_what_is_due_on_every_poll_until_stopped(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    record_everything(disktracker)
    know_listings(disktracker, [])
    polls: list[float] = []

    def due(_: Request) -> Response:
        # Due only on the second poll, as when its schedule fires or it is asked to run.
        polls.append(time.monotonic())
        sources = [spd_source(serverpartdeals)] if len(polls) == 2 else []
        return Response(json.dumps(sources), content_type="application/json")

    # Registered before environment's own answer, so it is the one given.
    disktracker.expect_request("/api/sources/due", method="GET").respond_with_handler(due)
    collector = start_loop(environment(disktracker))
    deadline = time.monotonic() + 30
    while (len(posts(disktracker)) < 3 or len(polls) < 4) and time.monotonic() < deadline:
        time.sleep(0.05)
    collector.send_signal(signal.SIGTERM)
    stdout, stderr = collector.communicate(timeout=30)

    assert collector.returncode == 0, stderr
    completed = [event for event in events(stdout) if event["event"] == "run_complete"]
    assert [event["recorded"] for event in completed] == [3]
    assert len(polls) >= 4


def test_each_run_reads_robots_txt_afresh_so_a_refusal_lasts_only_that_run(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    # The store refuses the first request for robots.txt, and answers the next.
    serverpartdeals.expect_oneshot_request("/robots.txt").respond_with_data("no", status=403)
    serve_feed(serverpartdeals, PAGE["products"])
    record_everything(disktracker)
    know_listings(disktracker, [])
    polls: list[float] = []

    def due(_: Request) -> Response:
        # Due until it has run twice.
        polls.append(time.monotonic())
        sources = [spd_source(serverpartdeals)] if len(run_reports(disktracker)) < 2 else []
        return Response(json.dumps(sources), content_type="application/json")

    disktracker.expect_request("/api/sources/due", method="GET").respond_with_handler(due)
    collector = start_loop(environment(disktracker))
    deadline = time.monotonic() + 30
    while len(run_reports(disktracker)) < 2 and time.monotonic() < deadline:
        time.sleep(0.05)
    collector.send_signal(signal.SIGTERM)
    stdout, stderr = collector.communicate(timeout=30)

    assert collector.returncode == 0, stderr
    runs = [
        event["event"]
        for event in events(stdout)
        if event["event"] in ("run_failed", "run_complete")
    ]
    assert runs == ["run_failed", "run_complete"]
    assert len(posts(disktracker)) == 3


def test_disktracker_going_away_mid_run_fails_each_offer_after_retrying(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    def go_away(_: Request) -> Response:
        # The run has its sources by the time it reaches the store.
        disktracker.stop()
        return Response(ALLOW_ALL, content_type="text/plain")

    serverpartdeals.expect_request("/robots.txt").respond_with_handler(go_away)
    serve_feed(serverpartdeals, PAGE["products"])

    result = run_collector(serverpartdeals, disktracker)

    # The run completes; the round then cannot learn what else is due, so it does not succeed.
    assert result.returncode == 1, result.stderr
    output = events(result.stdout)
    assert output[-1]["event"] == "sources_unavailable"
    failures = [event for event in output if event["event"] == "post_failed"]
    assert [(event["url"].rsplit("/", 1)[-1], event["status"]) for event in failures] == [
        ("seagate-exos-x20-st18000nm003d-18tb", None),
        ("wd-ultrastar-hc550-wuh721818ale6l4", None),
        ("intel-d3-s4510-960gb?variant=9003", None),
    ]
    [unchecked] = [event for event in output if event["event"] == "recheck_failed"]
    assert unchecked == {
        "event": "recheck_failed",
        "source": "serverpartdeals",
        "error": "[Errno 111] Connection refused",
    }
    [complete] = [event for event in output if event["event"] == "run_complete"]
    assert complete == {
        "event": "run_complete",
        "source": "serverpartdeals",
        "seen": 3,
        "recorded": 0,
        "queued": 0,
        "ignored": 0,
        "failed": 3,
        "rechecked": 0,
        "recheck_failed": 0,
        "stopped": False,
    }
    assert output[-2] == {
        "event": "run_report_failed",
        "source": "serverpartdeals",
        "error": "[Errno 111] Connection refused",
    }


def test_a_run_report_disktracker_rejects_is_a_warning_and_the_run_still_succeeds(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"][:1])
    record_everything(disktracker)
    know_listings(disktracker, [])
    disktracker.expect_oneshot_request("/api/collector-runs", method="POST").respond_with_data(
        "busy", status=503
    )

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    assert events(result.stdout)[-1] == {
        "event": "run_report_failed",
        "source": "serverpartdeals",
        "error": "runs: HTTP 503",
    }


def test_offers_that_left_the_feed_are_rechecked_on_their_own_page(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"][:1])
    base = base_of(serverpartdeals)
    for handle, price, available in [
        ("sold-out", TEN_THOUSAND_DOLLARS, False),
        ("sold-out-at-a-price", 46800, False),
        ("unlisted", 45000, True),
    ]:
        serverpartdeals.expect_request(f"/products/{handle}.js").respond_with_json(
            {"variants": [{"id": 1, "price": price, "available": available}]}
        )
    serverpartdeals.expect_request("/products/gone.js").respond_with_data("", status=404)
    serverpartdeals.expect_request("/products/broken.js").respond_with_data("", status=503)
    serverpartdeals.expect_request("/products/challenged.js").respond_with_data(
        "<html>Checking your browser</html>", content_type="text/html"
    )

    def known(handle: str, **fields: Any) -> dict[str, Any]:
        return listing_json(f"{base}/products/{handle}", title=f"Title of {handle}", **fields)

    know_listings(
        disktracker,
        [
            known("sold-out"),
            known("gone"),
            known("unlisted"),
            known("broken"),
            known("challenged"),
            known("already-sold-out", in_stock=False),
            known("marketplace", seller="Some shop"),
            listing_json(None, title="Entered by hand without a URL"),
            listing_json(
                f"{base}/collections/hard-drives/products/sold-out-at-a-price",
                title="Title of sold-out-at-a-price",
            ),
        ],
    )
    record_everything(disktracker)

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    fetched = sorted(
        request.path
        for request, _ in serverpartdeals.log
        if request.path not in (PRODUCTS, SSDS, "/robots.txt")
    )
    assert fetched == [
        f"/products/{handle}.js"
        for handle in (
            "broken",
            "challenged",
            "gone",
            "sold-out-at-a-price",
            "sold-out",
            "unlisted",
        )
    ]
    reposted = rechecks(disktracker)
    for offer in reposted:
        offer.pop("observed_at")

    def repost(url: str, title: str, price: int | None, in_stock: bool) -> dict[str, Any]:
        return {
            "source": "serverpartdeals",
            "seller": "",
            "url": url,
            "title": title,
            "mpn": "ST18000NM000J",
            "condition": "manufacturer_recertified",
            "capacity_gb": 18000,
            "item_price_cents": price,
            "shipping_cents": 0,
            "in_stock": in_stock,
            "aliases": [],
            "brand": None,
            "specifications": None,
        }

    assert reposted == [
        # Reported as the page shows it: disktracker records no price for a sold-out offer.
        repost(f"{base}/products/sold-out", "Title of sold-out", TEN_THOUSAND_DOLLARS, False),
        repost(f"{base}/products/gone", "Title of gone", None, False),
        repost(f"{base}/products/unlisted", "Title of unlisted", 45000, True),
        repost(
            f"{base}/collections/hard-drives/products/sold-out-at-a-price",
            "Title of sold-out-at-a-price",
            46800,
            False,
        ),
    ]
    output = events(result.stdout)
    failed = [event for event in output if event["event"] == "recheck_failed"]
    assert [(event["url"], event["error"][:29]) for event in failed] == [
        (f"{base}/products/broken", "Server error '503 SERVICE UNA"),
        (f"{base}/products/challenged", "Expecting value: line 1 colum"),
    ]
    assert output[-1] == {
        "event": "run_complete",
        "source": "serverpartdeals",
        "seen": 1,
        "recorded": 1,
        "queued": 0,
        "ignored": 0,
        "failed": 0,
        "rechecked": 6,
        "recheck_failed": 2,
        "stopped": False,
    }


def test_a_product_page_that_redirects_is_followed(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"][:1])
    base = base_of(serverpartdeals)
    serverpartdeals.expect_request("/products/moved.js").respond_with_response(
        Response(status=301, headers={"Location": f"{base}/canonical/moved.js"})
    )
    serverpartdeals.expect_request("/canonical/moved.js").respond_with_json(
        {"variants": [{"id": 1, "price": 46800, "available": False}]}
    )
    know_listings(disktracker, [listing_json(f"{base}/products/moved")])
    record_everything(disktracker)

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    [recheck] = rechecks(disktracker)
    assert (recheck["item_price_cents"], recheck["in_stock"]) == (46800, False)
    assert events(result.stdout)[-1]["failed"] == 0


def test_listings_disktracker_will_not_give_are_reported_and_the_run_completes(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"][:1])
    record_everything(disktracker)
    disktracker.expect_request("/api/listings", method="GET").respond_with_data(
        "unavailable", status=503
    )

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    output = events(result.stdout)
    assert output[1] == {
        "event": "recheck_failed",
        "source": "serverpartdeals",
        "error": "listings: HTTP 503",
    }
    assert (output[-1]["recorded"], output[-1]["rechecked"]) == (1, 0)


def test_listings_in_a_shape_the_collector_cannot_read_are_reported_and_the_run_completes(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"][:1])
    record_everything(disktracker)
    # An older disktracker, from before a listing named its store.
    older = listing_json(f"{base_of(serverpartdeals)}/products/known")
    del older["store"]
    know_listings(disktracker, [older])

    result = run_collector(serverpartdeals, disktracker)

    assert (result.returncode, result.stderr) == (0, "")
    output = events(result.stdout)
    assert output[1] == {
        "event": "recheck_failed",
        "source": "serverpartdeals",
        "error": "listings: the answer has no store",
    }
    assert (output[-1]["recorded"], output[-1]["rechecked"]) == (1, 0)


def test_solid_state_drives_are_collected_too_and_a_product_in_both_collections_once(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    nvme = {
        **PAGE["products"][2],
        "id": 7,
        "handle": "samsung-pm9a3-3-84tb-nvme",
        "title": "Samsung PM9A3 3.84TB NVMe U.2 SSD",
        "product_type": "Solid State Drives > 3.84TB > 2.5 > NVMe",
        "tags": ["capacity:3.84TB", "condition:New", "formFactor:2.5", "interface:PCIe Gen 4.0 x4"],
        "variants": [
            {
                "id": 71,
                "title": "Default Title",
                "sku": "MZQL23T8HCLS_NB",
                "price": "329.00",
                "available": True,
            }
        ],
    }
    serve_feed(serverpartdeals, PAGE["products"], ssds=[PAGE["products"][2], nvme])
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    posted = [json.loads(request.data) for request in posts(disktracker)]
    assert [offer["url"].rsplit("/", 1)[-1] for offer in posted] == [
        "seagate-exos-x20-st18000nm003d-18tb",
        "wd-ultrastar-hc550-wuh721818ale6l4",
        "intel-d3-s4510-960gb?variant=9003",
        "samsung-pm9a3-3-84tb-nvme",
    ]
    assert (posted[-1]["capacity_gb"], posted[-1]["specifications"]) == (
        3840,
        {"media_type": "ssd", "form_factor": "2_5", "interface": "nvme_pcie"},
    )
    assert events(result.stdout)[-1]["seen"] == 4


def test_paths_robots_txt_disallows_are_never_fetched(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(
        serverpartdeals, PAGE["products"][:1], robots="User-agent: *\nDisallow: /products/\n"
    )
    base = base_of(serverpartdeals)
    know_listings(disktracker, [listing_json(f"{base}/products/sold-out")])
    record_everything(disktracker)

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    assert "/products/sold-out.js" not in [request.path for request, _ in serverpartdeals.log]
    agents = {request.headers["User-Agent"] for request, _ in serverpartdeals.log}
    assert agents == {"disktracker-collector/0.1 (personal drive price tracker)"}
    output = events(result.stdout)
    assert [event for event in output if event["event"] == "recheck_failed"] == [
        {
            "event": "recheck_failed",
            "source": "serverpartdeals",
            "url": f"{base}/products/sold-out",
            "error": f"robots.txt disallows {base}/products/sold-out.js",
        }
    ]
    assert (output[-1]["recorded"], output[-1]["rechecked"], output[-1]["recheck_failed"]) == (
        1,
        1,
        1,
    )


@pytest.mark.parametrize(
    ("robots_status", "outcome"),
    [
        (404, "run_complete"),
        (403, "robots.txt disallows {base}/collections/hard-drives/products.json?limit=250&page=1"),
        (503, "robots.txt: HTTP 503"),
        (None, "robots.txt: [Errno 111] Connection refused"),
    ],
    ids=["no robots.txt", "forbidden", "robots.txt failing", "site unreachable"],
)
def test_a_site_without_readable_robots_rules_is_only_collected_when_it_has_none(
    serverpartdeals: HTTPServer, disktracker: HTTPServer, robots_status: int | None, outcome: str
) -> None:
    base = base_of(serverpartdeals)
    if robots_status is None:
        serverpartdeals.stop()
    else:
        serverpartdeals.expect_request("/robots.txt").respond_with_data("", status=robots_status)
        for collection, products in ((PRODUCTS, PAGE["products"][:1]), (SSDS, [])):
            serverpartdeals.expect_request(
                collection, query_string="limit=250&page=1"
            ).respond_with_json({"products": products})
            serverpartdeals.expect_request(
                collection, query_string="limit=250&page=2"
            ).respond_with_json({"products": []})
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    last = events(result.stdout)[-1]
    if outcome == "run_complete":
        assert (result.returncode, last["event"], last["recorded"]) == (0, "run_complete", 1)
    else:
        assert result.returncode == 1
        assert last == {
            "event": "run_failed",
            "source": "serverpartdeals",
            "seen": 0,
            "recorded": 0,
            "queued": 0,
            "ignored": 0,
            "failed": 0,
            "error": outcome.format(base=base),
        }
        assert posts(disktracker) == []


ISO_UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?Z$")


def test_every_log_line_says_when_how_severe_and_which_part_wrote_it(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"])
    rejected = json.dumps({"detail": [{"loc": ["body", "url"], "msg": "bad", "type": "x"}]})
    reply_in_turn(
        disktracker,
        [
            (rejected, 422),
            (scraped("recorded", listing_id=UUID(int=2)), 201),
            (scraped("recorded", listing_id=UUID(int=3)), 201),
        ],
    )
    know_listings(disktracker, [])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 0, result.stderr
    lines = log_lines(result.stdout)
    assert all(ISO_UTC.match(line["ts"]) for line in lines), lines
    assert [(line["event"], line["level"], line["logger"]) for line in lines] == [
        ("run_started", "INFO", "collector.collection"),
        ("post_failed", "WARNING", "collector.clients.disktracker"),
        ("run_complete", "INFO", "collector.collection"),
    ]


def test_a_crash_is_logged_as_an_error_with_its_traceback(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    malformed = {key: value for key, value in PAGE["products"][0].items() if key != "variants"}
    serve_feed(serverpartdeals, [malformed])

    result = run_collector(serverpartdeals, disktracker)

    assert result.returncode == 1
    crash = log_lines(result.stdout)[-1]
    assert (crash["event"], crash["level"], crash["logger"], crash["error"]) == (
        "run_crashed",
        "ERROR",
        "collector.schedule",
        "KeyError('variants')",
    )
    assert crash["exc_info"].startswith("Traceback (most recent call last):")
    assert crash["exc_info"].endswith("KeyError: 'variants'")


def test_debug_logging_shows_every_request_the_collector_makes(
    serverpartdeals: HTTPServer, disktracker: HTTPServer
) -> None:
    serve_feed(serverpartdeals, PAGE["products"][:1])
    record_everything(disktracker)
    know_listings(disktracker, [])

    result = run({**collector_env(serverpartdeals, disktracker), "LOG_LEVEL": "DEBUG"})

    assert result.returncode == 0, result.stderr
    requests = [
        line["event"]
        for line in log_lines(result.stdout)
        if line["logger"] == "httpx" and line["level"] == "INFO"
    ]
    base = base_of(serverpartdeals)
    assert any(request.startswith(f"HTTP Request: GET {base}/robots.txt") for request in requests)
    assert any(
        request.startswith(f"HTTP Request: POST {base_of(disktracker)}/api/scraped")
        for request in requests
    )
    assert any(
        line["event"] == "offer_posted" and line["level"] == "DEBUG"
        for line in log_lines(result.stdout)
    )
