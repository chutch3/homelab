from __future__ import annotations

import dataclasses
import os
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
            "COVERAGE_PROCESS_START": str(APP_DIR / "pyproject.toml"),
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


def prime_radarr(server: HTTPServer, *, missing=(), cutoff=()) -> None:
    _prime_arr(server, missing=missing, cutoff=cutoff)


def prime_sonarr(server: HTTPServer, *, missing=(), cutoff=()) -> None:
    _prime_arr(server, missing=missing, cutoff=cutoff)


def _prime_arr(server: HTTPServer, *, missing=(), cutoff=()) -> None:
    server.expect_request("/api/v3/wanted/missing").respond_with_json(
        {"records": [{"id": i, "title": t} for i, t in missing]})
    server.expect_request("/api/v3/wanted/cutoff").respond_with_json(
        {"records": [{"id": i, "title": t} for i, t in cutoff]})
    server.expect_request("/api/v3/command", method="POST").respond_with_json({"id": 1})


def prime_prowlarr(server: HTTPServer, *, apps=(), indexers=()) -> None:
    server.expect_request("/api/v1/applications").respond_with_json(list(apps))
    server.expect_request("/api/v1/indexer").respond_with_json(list(indexers))


def down(server: HTTPServer) -> None:
    server.expect_request("/api/v3/wanted/missing").respond_with_data("boom", status=500)
    server.expect_request("/api/v1/applications").respond_with_data("boom", status=500)
    server.expect_request("/api/v1/indexer").respond_with_data("boom", status=500)
