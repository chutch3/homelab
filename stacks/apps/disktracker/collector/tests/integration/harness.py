"""What the collector's integration tests share: the fake disktracker, running the real
collector process, and reading what it did."""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from uuid import UUID

from pytest_httpserver import HTTPServer
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


def serve_condition_rules(disktracker: HTTPServer, rules: list[dict[str, str]]) -> None:
    """Rules served before environment() are the ones the collector gets."""
    disktracker.expect_request("/api/condition-rules", method="GET").respond_with_json(rules)


def serve_sources(disktracker: HTTPServer, sources: list[dict[str, Any]]) -> None:
    disktracker.expect_request("/api/sources/due", method="GET").respond_with_json(sources)


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


def know_listings(
    disktracker: HTTPServer, listings: list[dict[str, Any]], store: str = "serverpartdeals"
) -> None:
    disktracker.expect_request(
        "/api/listings", method="GET", query_string=f"store={store}"
    ).respond_with_json(listings)


def record_everything(disktracker: HTTPServer) -> None:
    disktracker.expect_request("/api/scraped", method="POST").respond_with_json(
        {"status": "recorded", "listing_id": str(RECORDED), "unmatched_id": None}, status=201
    )


def reply_in_turn(disktracker: HTTPServer, replies: list[tuple[str, int]]) -> None:
    """Answer successive posts with these raw bodies and statuses, in order."""
    pending = iter(replies)

    def reply(_request: Request) -> Response:
        body, status = next(pending)
        return Response(body, status=status, content_type="application/json")

    disktracker.expect_request("/api/scraped", method="POST").respond_with_handler(reply)


def scraped(status: str, listing_id: UUID | None = None, unmatched_id: UUID | None = None) -> str:
    return json.dumps(
        {
            "status": status,
            "listing_id": str(listing_id) if listing_id else None,
            "unmatched_id": str(unmatched_id) if unmatched_id else None,
        }
    )


def posts(disktracker: HTTPServer) -> list[Request]:
    """The offers posted to disktracker, in order."""
    return [request for request, _ in disktracker.log if request.path == "/api/scraped"]


def run_reports(disktracker: HTTPServer) -> list[dict[str, Any]]:
    return [
        json.loads(request.data)
        for request, _ in disktracker.log
        if request.path == "/api/collector-runs"
    ]


def progress_reports(disktracker: HTTPServer) -> list[dict[str, Any]]:
    """What the collector said of how far its runs had got, in order."""
    return [
        json.loads(request.data)
        for request, _ in disktracker.log
        if request.path == "/api/collector-activity"
    ]


def rechecks(disktracker: HTTPServer) -> list[dict[str, Any]]:
    """What was posted after the run asked disktracker for its listings: the rechecked offers."""
    paths = [request.path for request, _ in disktracker.log]
    after = paths.index("/api/listings") + 1
    return [
        json.loads(request.data)
        for request, _ in disktracker.log[after:]
        if request.path == "/api/scraped"
    ]
