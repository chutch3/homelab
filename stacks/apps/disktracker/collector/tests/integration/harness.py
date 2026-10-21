"""What the collector's integration tests share: the fake disktracker, running the real
collector process, and reading what it did."""

import json
import os
import re
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
from uuid import UUID

from pytest_httpserver import HTTPServer
from pytest_httpserver.httpserver import QueryMatcher
from werkzeug import Request, Response

ROOT = Path(__file__).parents[2]
RECORDED = UUID(int=1)
ALLOW_ALL = "User-agent: *\nDisallow:\n"


def source_json(
    key: str, kind: str, base_url: str, settings: dict[str, Any], **fields: Any
) -> dict[str, Any]:
    """A source as disktracker's API describes it."""
    return {
        "id": str(UUID(int=len(key))),
        "key": key,
        "name": key,
        "kind": kind,
        "base_url": base_url,
        "settings": settings,
        "schedule": "0 */8 * * *",
        "enabled": True,
        "transport": "direct",
        "basis": "unconfirmed",
        "obey_robots": True,
        "notes": "",
        "next_run_at": None,
        **fields,
    }


# The condition rules disktracker is seeded with.
SEEDED_CONDITION_RULES = [
    {"pattern": r"\bmanufacturer recertified\b", "condition": "manufacturer_recertified"},
    {"pattern": r"\bseller refurbished\b", "condition": "refurbished"},
    {"pattern": r"\bopen box\b", "condition": "used"},
    {"pattern": r"\brecertified\b", "condition": "refurbished"},
    {"pattern": r"\brefurbished\b", "condition": "refurbished"},
    {"pattern": r"\brenewed\b", "condition": "refurbished"},
    {"pattern": r"\bused\b", "condition": "used"},
    {"pattern": r"\bnew\b", "condition": "new"},
]


RUNS = "/api/collection-runs"
# A run of the collector's, by the id it chose.
A_RUN = re.compile(r"^/api/collection-runs/[0-9a-f-]+$")
# Asking which sources are due.
DUE = ("/api/sources",)
DUE_QUERY = {"method": "GET", "query_string": "due=true"}


def run_answer(request: Request, stop_requested: bool = False) -> Response:
    """A run as disktracker answers with it: started (201), or updated as the request says."""
    body = json.loads(request.data)
    run_id = body.get("id") or request.path.rsplit("/", 1)[1]
    run = {
        "id": run_id, "source": body.get("source", "store"), "status": body.get("status", "running"),
        "started_at": body.get("started_at", "2026-09-27T08:00:00Z"),
        "updated_at": "2026-09-27T08:00:00Z", "finished_at": body.get("finished_at"),
        "reason": body.get("reason"),
        "seen": 0, "recorded": 0, "queued": 0, "ignored": 0, "failed": 0, "rechecked": 0,
        "recheck_failed": 0, **{key: value for key, value in body.items() if isinstance(value, int)},
        "stop_requested": stop_requested,
    }  # fmt: skip
    status = 201 if request.method == "POST" else 200
    return Response(json.dumps(run), status=status, content_type="application/json")


def serve_runs(disktracker: HTTPServer, update: Callable[[Request], Response] = run_answer) -> None:
    """Every run registered, its updates answered (by default: progress heard without asking
    it to stop, and its end taken), and every heartbeat heard."""
    disktracker.expect_request(RUNS, method="POST").respond_with_handler(run_answer)
    disktracker.expect_request(A_RUN, method="PATCH").respond_with_handler(update)
    disktracker.expect_request("/api/collector-heartbeat", method="PUT").respond_with_json(
        {"seen_at": "2026-09-27T08:00:00Z"}
    )


def serve_condition_rules(disktracker: HTTPServer, rules: list[dict[str, str]]) -> None:
    """Rules served before environment() are the ones the collector gets."""
    disktracker.expect_request("/api/condition-rules", method="GET").respond_with_json(rules)


def serve_sources(disktracker: HTTPServer, sources: list[dict[str, Any]]) -> None:
    disktracker.expect_request(*DUE, **DUE_QUERY).respond_with_json(sources)


def environment(
    disktracker: HTTPServer, *sources: dict[str, Any], **settings: str
) -> dict[str, str]:
    """Run against fakes: disktracker at its URL, configured with these sources."""
    serve_sources(disktracker, list(sources))
    serve_condition_rules(disktracker, SEEDED_CONDITION_RULES)
    return {
        **os.environ,
        "DISKTRACKER_URL": base_of(disktracker),
        "COLLECTOR_RETRY_DELAY_SECONDS": "0",
        "COLLECTOR_MIN_DELAY_SECONDS": "0",
        **settings,
    }


def run(env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "collector"],
        cwd=ROOT,
        env={**env, "COLLECTOR_RUN_ONCE": "1"},
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def start_loop(env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-m", "collector"],
        cwd=ROOT,
        # Asks what is due every tenth of a second.
        env={**env, "COLLECTOR_POLL_SECONDS": "0.1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def base_of(server: HTTPServer) -> str:
    return server.url_for("").rstrip("/")


METADATA = ("ts", "level", "logger", "exc_info")


def log_lines(stdout: str) -> list[dict[str, Any]]:
    """Every JSON log line the collector wrote, whole."""
    return [json.loads(line) for line in stdout.strip().splitlines()]


def events(stdout: str) -> list[dict[str, Any]]:
    """The collector's own log lines, without when/level/where metadata: what happened."""
    return [
        {key: value for key, value in line.items() if key not in METADATA}
        for line in log_lines(stdout)
        if line.get("logger", "collector").startswith("collector")
    ]


def serve_robots(server: HTTPServer, rules: str = ALLOW_ALL) -> None:
    server.expect_request("/robots.txt").respond_with_data(rules, content_type="text/plain")


class OfStore(QueryMatcher):
    """A query for one store's offers, whatever else it says (the client sends its defaults)."""

    def __init__(self, store: str) -> None:
        self.store = store

    def get_comparing_values(self, request_query_string: bytes) -> tuple[Any, Any]:
        return parse_qs(request_query_string.decode()).get("store"), [self.store]


def know_offers(
    disktracker: HTTPServer, offers: list[dict[str, Any]], store: str = "serverpartdeals"
) -> None:
    disktracker.expect_request(
        "/api/offers", method="GET", query_string=OfStore(store)
    ).respond_with_json(offers)


# Where the collector sends what it read: a page afresh is taken in, and a recheck of an offer
# disktracker knows is a price of it.
INGESTIONS, PRICES = "/api/ingestions", "/api/prices"


def record_everything(disktracker: HTTPServer) -> None:
    for path in (INGESTIONS, PRICES):
        disktracker.expect_request(path, method="POST").respond_with_json(
            {"status": "recorded", "offer_id": str(RECORDED), "price_id": None,
             "review_item_id": None},
            status=201,
        )  # fmt: skip


def reply_in_turn(disktracker: HTTPServer, replies: list[tuple[str, int]]) -> None:
    """Answer successive posts with these raw bodies and statuses, in order."""
    pending = iter(replies)

    def reply(_request: Request) -> Response:
        body, status = next(pending)
        return Response(body, status=status, content_type="application/json")

    for path in (INGESTIONS, PRICES):
        disktracker.expect_request(path, method="POST").respond_with_handler(reply)


def scraped(status: str, offer_id: UUID | None = None, review_item_id: UUID | None = None) -> str:
    """What disktracker answers a submitted price with."""
    return json.dumps(
        {
            "status": status,
            "offer_id": str(offer_id) if offer_id else None,
            "price_id": None,
            "review_item_id": str(review_item_id) if review_item_id else None,
        }
    )


def posts(disktracker: HTTPServer) -> list[Request]:
    """The pages posted to disktracker afresh, in order."""
    return [request for request, _ in disktracker.log if request.path == INGESTIONS]


def run_reports(disktracker: HTTPServer) -> list[dict[str, Any]]:
    """How each run ended, with its source and start: one for each run whose end was taken
    (repeated ends, sent again after a lost answer, count once)."""
    started = {
        body["id"]: body
        for body in (json.loads(r.data) for r, _ in disktracker.log if r.path == RUNS)
    }
    ends: dict[str, dict[str, Any]] = {}
    for request, response in disktracker.log:
        body = json.loads(request.data) if request.method == "PATCH" else {}
        if body.get("status", "running") != "running" and response.status_code == 200:
            run_id = request.path.rsplit("/", 1)[1]
            start = started[run_id]
            ends[run_id] = {"source": start["source"], "started_at": start["started_at"], **body}
    return list(ends.values())


def progress_reports(disktracker: HTTPServer) -> list[dict[str, Any]]:
    """What the collector said of how far its runs had got, in order."""
    return [
        json.loads(request.data)
        for request, _ in disktracker.log
        if request.method == "PATCH" and "status" not in json.loads(request.data)
    ]


def heartbeats(disktracker: HTTPServer) -> list[list[str]]:
    """The runs the collector named in each heartbeat, in order."""
    return [
        json.loads(request.data)["runs"]
        for request, _ in disktracker.log
        if request.path == "/api/collector-heartbeat"
    ]


def rechecks(disktracker: HTTPServer) -> list[dict[str, Any]]:
    """What was posted after the run asked disktracker for the offers it knows: the rechecked offers."""
    paths = [request.path for request, _ in disktracker.log]
    after = paths.index("/api/offers") + 1
    return [
        json.loads(request.data) for request, _ in disktracker.log[after:] if request.path == PRICES
    ]
