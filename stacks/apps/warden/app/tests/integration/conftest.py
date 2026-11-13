from __future__ import annotations

import dataclasses
import json
import os
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from prometheus_client.parser import text_string_to_metric_families
from pytest_httpserver import HTTPServer

from tests.profile_data import CUSTOM_FORMAT, PROFILE, REMOTE_FORMAT, REMOTE_PROFILE

APP_DIR = Path(__file__).resolve().parents[2]
EXAMPLES = APP_DIR.parent / "examples/profiles"
CLI = str(Path(sys.executable).with_name("warden"))


def cli_env(directory: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("WARDEN_")}
    env.update(PYTHONDONTWRITEBYTECODE="1", WARDEN_DB_URL=f"sqlite:///{directory}/must-not-create.db",
               WARDEN_METRICS_PORT="invalid-server-setting")
    return env


def invoke(directory: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [CLI, *args], cwd=directory, env=env if env is not None else cli_env(directory),
        capture_output=True, text=True, timeout=15,
    )


def run_validate(directory: Path) -> subprocess.CompletedProcess[str]:
    return invoke(directory.parent, "profiles", "validate", "--directory", str(directory))


def run_dump(server: HTTPServer, output: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = cli_env(output.parent)
    env.update(WARDEN_RADARR_URL=server.url_for(""), WARDEN_RADARR_API_KEY="secret-test-key")
    return invoke(output.parent, "profiles", "dump", "--source", "radarr", "--output", str(output), *args, env=env)


def run_diff(
    server: HTTPServer, directory: Path, *args: str, env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    settings = cli_env(directory.parent)
    settings.update(WARDEN_RADARR_URL=server.url_for(""), WARDEN_RADARR_API_KEY="test-key")
    settings.update(env or {})
    return invoke(directory.parent, "profiles", "diff", "--source", "radarr", "--directory", str(directory), *args, env=settings)


@pytest.fixture()
def output_directory() -> Iterator[Path]:
    with TemporaryDirectory(prefix="warden-cli-test-", dir="/dev/shm") as directory:
        yield Path(directory) / "catalog"


@pytest.fixture()
def catalog(tmp_path: Path) -> Path:
    root = tmp_path / "catalog"
    for source in ("radarr", "sonarr"):
        profiles = root / source / "profiles"
        formats = root / source / "custom_formats"
        profiles.mkdir(parents=True)
        formats.mkdir()
        (profiles / "hd.yml").write_text(PROFILE)
        (formats / "preferred.json").write_text(json.dumps(CUSTOM_FORMAT))
    return root


def dump_catalog(server: HTTPServer, directory: Path) -> None:
    server.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    server.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    result = run_dump(server, directory)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Exported 1 profiles and 1 custom formats.\n"


@pytest.fixture()
def dumped_catalog(httpserver: HTTPServer, output_directory: Path) -> Path:
    dump_catalog(httpserver, output_directory)
    httpserver.clear_log()
    return output_directory


def git(directory: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True, check=True, timeout=15,
    ).stdout.strip()


def commit(directory: Path, message: str) -> str:
    git(directory, "add", ".")
    git(directory, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", message)
    return git(directory, "rev-parse", "HEAD")


@pytest.fixture()
def repository(httpserver: HTTPServer, output_directory: Path) -> Path:
    dump_catalog(httpserver, output_directory)
    git(output_directory, "init", "-b", "main")
    commit(output_directory, "initial catalog")
    return output_directory


def stop_server(handle: WardenHandle) -> None:
    if handle.proc.poll() is None:
        handle.proc.send_signal(signal.SIGTERM)
        try:
            handle.proc.wait(timeout=15)
        finally:
            if handle.proc.poll() is None:
                handle.proc.kill()
                handle.proc.wait(timeout=5)


def profile_events(handle: WardenHandle) -> list[dict]:
    records = [json.loads(line) for line in handle.logfile.read_text().splitlines() if line.startswith("{")]
    return [record for record in records if record.get("event") == "profile_checked"]


def start_observer(
    directory: Path, server: HTTPServer, launch: Callable[..., WardenHandle], **overrides: str,
) -> WardenHandle:
    prime_radarr(server)
    server.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    server.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    return launch(**{
        "WARDEN_RADARR_URL": server.url_for(""), "WARDEN_RADARR_API_KEY": "test-key",
        "WARDEN_PROFILES_REPO": str(directory), "WARDEN_PROFILES_REF": "main",
        "WARDEN_PROFILES_CACHE_DIR": str(directory.parent / "cache"),
        "WARDEN_PROFILES_INTERVAL_SEC": "0.2", "WARDEN_PROFILES_TIMEOUT_SEC": "2",
        **overrides,
    })


def pytest_collection_finish(session: pytest.Session) -> None:
    """Apply the coverage gate to the combined suite, not an isolated test tier."""
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
            **cli_env(tmp_path),
            "WARDEN_METRICS_PORT": str(port),
            "WARDEN_DB_URL": f"sqlite:///{tmp_path}/warden-{port}.db",
            "WARDEN_POLL_INTERVAL_SEC": "0.5",
            "WARDEN_FALLBACK_SEARCHES_PER_DAY": "500",
            **env_overrides,
        }
        with logfile.open("w") as stream:
            proc = subprocess.Popen(
                [CLI, "serve"], cwd=tmp_path, env=env,
                stdout=stream, stderr=subprocess.STDOUT, text=True,
            )
        handle = WardenHandle(base_url=f"http://127.0.0.1:{port}", proc=proc, logfile=logfile)
        handles.append(handle)
        _wait_healthz(handle, timeout=40.0)
        return handle

    yield _launch

    for handle in handles:
        stop_server(handle)


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
