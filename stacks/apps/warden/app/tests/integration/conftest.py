from __future__ import annotations

import dataclasses
import os
import re
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from pathlib import Path

import pytest
from prometheus_client.parser import text_string_to_metric_families
from pytest_httpserver import HTTPServer

APP_DIR = Path(__file__).resolve().parents[2]  # .../warden/app


def pytest_collection_finish(session: pytest.Session) -> None:
    """Disable coverage fail-under when only integration tests are collected (no unit tests).

    Mirrors fiber: the gated subprocess suite is coverage-exempt; the ≥90% gate is
    carried by the unit tier and enforced on the full run.
    """
    has_unit = any("tests/unit" in str(item.fspath) for item in session.items)
    if not has_unit:
        for _name, plugin in session.config.pluginmanager.list_name_plugin():
            if hasattr(plugin, "options") and hasattr(plugin.options, "cov_fail_under"):
                plugin.options.cov_fail_under = None
                break


@dataclasses.dataclass
class WardenHandle:
    base_url: str
    proc: subprocess.Popen
    logfile: Path


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _server() -> Iterable[HTTPServer]:
    srv = HTTPServer(host="127.0.0.1")
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture()
def radarr_server():
    yield from _server()


@pytest.fixture()
def sonarr_server():
    yield from _server()


@pytest.fixture()
def prowlarr_server():
    yield from _server()


@pytest.fixture()
def launch(tmp_path) -> Callable[..., WardenHandle]:
    handles: list[WardenHandle] = []

    def _launch(**env_overrides: str) -> WardenHandle:
        port = _free_port()
        logfile = tmp_path / f"warden-{port}.log"
        env = {
            **os.environ,
            "WARDEN_METRICS_PORT": str(port),
            "WARDEN_DB_URL": f"sqlite:///{tmp_path}/warden-{port}.db",
            "WARDEN_POLL_INTERVAL_SEC": "0.5",
            "WARDEN_FALLBACK_SEARCHES_PER_DAY": "500",
            **env_overrides,
        }
        fh = open(logfile, "w")
        proc = subprocess.Popen(
            ["uv", "run", "python", "-m", "warden.main"],
            cwd=str(APP_DIR), env=env, stdout=fh, stderr=subprocess.STDOUT, text=True,
        )
        handle = WardenHandle(base_url=f"http://127.0.0.1:{port}", proc=proc, logfile=logfile)
        handles.append(handle)
        _wait_healthz(handle, timeout=40.0)
        return handle

    yield _launch

    for h in handles:
        if h.proc.poll() is None:
            h.proc.send_signal(signal.SIGTERM)
            try:
                h.proc.wait(timeout=15)
            except subprocess.TimeoutExpired:
                h.proc.kill()
                h.proc.wait()


def _wait_healthz(handle: WardenHandle, *, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if handle.proc.poll() is not None:
            raise AssertionError(f"warden exited early ({handle.proc.returncode}):\n{handle.logfile.read_text()}")
        try:
            with urllib.request.urlopen(f"{handle.base_url}/healthz", timeout=2) as r:
                if r.status == 200:
                    return
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(0.2)
    raise AssertionError(f"warden /healthz not ready in {timeout}s:\n{handle.logfile.read_text()}")


def scrape(handle: WardenHandle) -> str:
    with urllib.request.urlopen(f"{handle.base_url}/metrics", timeout=5) as r:
        return r.read().decode()


def sample(text: str, name: str, **labels: str) -> float | None:
    for fam in text_string_to_metric_families(text):
        for s in fam.samples:
            if s.name == name and all(s.labels.get(k) == v for k, v in labels.items()):
                return s.value
    return None


def poll_until(fn, *, timeout: float = 10.0, interval: float = 0.2):
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = fn()
        if last:
            return last
        time.sleep(interval)
    return last


def _records(server: HTTPServer, path: str, method: str | None = None) -> list:
    out = []
    for req, _resp in server.log:
        if req.path == path and (method is None or req.method == method):
            out.append(req)
    return out


def commands(server: HTTPServer) -> list[dict]:
    return [r.get_json() for r in _records(server, "/api/v3/command", "POST")]


def prime_radarr(server: HTTPServer, *, missing=(), cutoff=(), queue=(), grab_ids=(),
                 free_space=None) -> None:
    _prime_arr(server, missing=missing, cutoff=cutoff, queue=queue, grab_ids=grab_ids,
               id_field="movieId", free_space=free_space)


def prime_sonarr(server: HTTPServer, *, missing=(), cutoff=(), queue=(), grab_ids=(),
                 free_space=None) -> None:
    _prime_arr(server, missing=missing, cutoff=cutoff, queue=queue, grab_ids=grab_ids,
               id_field="episodeId", free_space=free_space)


def _missing_record(m) -> dict:
    # accept either a full dict (with optional lastSearchTime) or an (id, title) tuple
    return m if isinstance(m, dict) else {"id": m[0], "title": m[1]}


def _history_handler(grab_ids, id_field: str):
    """history/since handler: returns a grab for each grab_id stamped at request-time, so the
    grab always post-dates warden's search (the hit correlation requires grab.at >= searched_at)."""
    import json as _json
    from datetime import datetime, timezone

    from werkzeug import Response

    def handler(request):
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        rows = [{id_field: rid, "date": now,
                 "data": {"indexer": "TestIndexer", "releaseSource": "UserInvokedSearch"}}
                for rid in grab_ids]
        return Response(_json.dumps(rows), content_type="application/json")

    return handler


def _prime_arr(server: HTTPServer, *, missing=(), cutoff=(), queue=(), grab_ids=(),
               id_field="movieId", free_space=None) -> None:
    server.expect_request("/api/v3/wanted/missing").respond_with_json(
        {"records": [_missing_record(m) for m in missing]})
    server.expect_request("/api/v3/wanted/cutoff").respond_with_json(
        {"records": [{"id": i, "title": t} for i, t in cutoff]})
    server.expect_request("/api/v3/command", method="POST").respond_with_json({"id": 1})
    server.expect_request("/api/v3/queue").respond_with_json({"records": list(queue)})
    server.expect_request(re.compile(r"^/api/v3/queue/\d+$"), method="DELETE").respond_with_json({})
    server.expect_request("/api/v3/history/since").respond_with_handler(
        _history_handler(grab_ids, id_field))
    # rootfolder feeds the space guard; free_space=None => no accessible reading (guard fails open).
    server.expect_request("/api/v3/rootfolder").respond_with_json(
        [] if free_space is None
        else [{"path": "/data", "accessible": True, "freeSpace": free_space}])


def deletes(server: HTTPServer) -> list:
    return [req for req, _resp in server.log
            if req.method == "DELETE" and req.path.startswith("/api/v3/queue/")]


def queue_fetches(server: HTTPServer) -> int:
    return sum(1 for req, _ in server.log if req.path == "/api/v3/queue")


def prime_progressing(server: HTTPServer, *, queue_id: int, remote_id: int, id_field: str,
                      start_left: int, step: int) -> None:
    """A download whose sizeleft shrinks by `step` on every /queue fetch (never bottoms out) —
    a genuinely-progressing item that no-progress detection must NOT remove."""
    import json as _json

    from werkzeug import Response

    state = {"left": start_left}

    def handler(request):
        rec = {"id": queue_id, id_field: remote_id, "title": "ok", "status": "downloading",
               "errorMessage": None, "added": "2026-06-15T00:00:00Z",
               "downloadId": f"DL{queue_id}", "size": start_left, "sizeleft": state["left"]}
        state["left"] -= step
        return Response(_json.dumps({"records": [rec]}), content_type="application/json")

    server.expect_request("/api/v3/queue").respond_with_handler(handler)
    server.expect_request("/api/v3/wanted/missing").respond_with_json({"records": []})
    server.expect_request("/api/v3/wanted/cutoff").respond_with_json({"records": []})
    server.expect_request("/api/v3/command", method="POST").respond_with_json({"id": 1})
    server.expect_request(re.compile(r"^/api/v3/queue/\d+$"), method="DELETE").respond_with_json({})


def stale_record(remote_id: int, queue_id: int, *, id_field: str, age_days: int = 3,
                 status: str = "warning", err: str = "The download is stalled with no connections") -> dict:
    from datetime import datetime, timedelta, timezone
    added = (datetime.now(timezone.utc) - timedelta(days=age_days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": queue_id, id_field: remote_id, "title": f"item-{remote_id}",
            "status": status, "errorMessage": err, "added": added}


def prime_prowlarr(server: HTTPServer, *, apps=(), indexers=()) -> None:
    server.expect_request("/api/v1/applications").respond_with_json(list(apps))
    server.expect_request("/api/v1/indexer").respond_with_json(list(indexers))


def down(server: HTTPServer) -> None:
    server.expect_request("/api/v3/wanted/missing").respond_with_data("boom", status=500)
    server.expect_request("/api/v1/applications").respond_with_data("boom", status=500)
    server.expect_request("/api/v1/indexer").respond_with_data("boom", status=500)
