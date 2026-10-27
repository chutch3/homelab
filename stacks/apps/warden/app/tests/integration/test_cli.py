from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pytest_httpserver import HTTPServer

from tests.integration.conftest import WardenHandle, _wait_healthz, poll_until, prime_radarr, sample, scrape
from tests.integration.test_profile_dump import REMOTE_FORMAT, REMOTE_PROFILE, output_directory


pytestmark = pytest.mark.integration
APP_DIR = Path(__file__).resolve().parents[2]
EXAMPLES = APP_DIR.parent / "examples/profiles"


def cli_env(directory: Path) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("WARDEN_")}
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(APP_DIR),
               WARDEN_DB_URL=f"sqlite:///{directory}/must-not-create.db",
               WARDEN_METRICS_PORT="invalid-server-setting")
    return env


def invoke(directory: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "warden", *args], cwd=directory,
        env=env if env is not None else cli_env(directory), capture_output=True, text=True, timeout=15,
    )


@pytest.mark.parametrize("args", [(), ("--help",)])
def test_help_lists_commands_without_starting_the_server(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = invoke(tmp_path, *args)
    assert result.returncode == 0, result.stderr
    assert "serve" in result.stdout and "profiles" in result.stdout
    assert result.stderr == ""
    assert not (tmp_path / "must-not-create.db").exists()


@pytest.mark.parametrize("args", [("unknown",), ("serve", "--unknown"), ("profiles",), ("profiles", "dump")])
def test_invalid_commands_report_usage_without_starting_the_server(tmp_path: Path, args: tuple[str, ...]) -> None:
    result = invoke(tmp_path, *args)
    assert result.returncode == 2
    assert "usage: warden" in result.stderr
    assert result.stdout == ""
    assert not (tmp_path / "must-not-create.db").exists()


def test_profiles_validate_without_server_configuration(tmp_path: Path) -> None:
    result = invoke(tmp_path, "profiles", "validate", "--directory", str(EXAMPLES))
    assert result.returncode == 0, result.stderr
    assert result.stdout == "Valid catalog: 1 profiles, 1 custom formats.\n"
    assert not (tmp_path / "must-not-create.db").exists()


def test_profiles_validation_error_retains_exit_status(tmp_path: Path) -> None:
    result = invoke(tmp_path, "profiles", "validate", "--directory", str(tmp_path / "missing"))
    assert result.returncode == 1
    assert "catalog directory does not exist" in result.stderr
    assert result.stdout == ""
    assert not (tmp_path / "must-not-create.db").exists()


def test_profiles_dump_and_diff_remain_read_only(httpserver: HTTPServer, output_directory: Path) -> None:
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    work = output_directory.parent
    env = cli_env(work)
    env.update(WARDEN_RADARR_URL=httpserver.url_for(""), WARDEN_RADARR_API_KEY="test-key")
    dumped = invoke(work, "profiles", "dump", "--source", "radarr", "--output", str(output_directory), env=env)
    assert dumped.returncode == 0, dumped.stderr
    assert dumped.stdout == "Exported 1 profiles and 1 custom formats.\n"
    args = ("profiles", "diff", "--source", "radarr", "--directory", str(output_directory), "--json")
    clean = invoke(work, *args, env=env)
    assert clean.returncode == 0, clean.stderr
    assert json.loads(clean.stdout) == {"source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": []}
    path = output_directory / "radarr/profiles/HD.yml"
    profile = yaml.safe_load(path.read_text())
    profile["quality_profiles"][0]["custom_format_scores"]["Preferred"] = 250
    path.write_text(yaml.safe_dump(profile))
    drift = invoke(work, *args, env=env)
    assert drift.returncode == 2, drift.stderr
    assert json.loads(drift.stdout)["changes"] == [
        {"kind": "profile", "name": "HD", "field": "custom_format_scores.Preferred", "current": 100, "desired": 250},
    ]
    assert [(request.method, request.path) for request, _ in httpserver.log] == [
        ("GET", "/api/v3/qualityprofile"), ("GET", "/api/v3/customformat"),
    ] * 3
    assert not (work / "must-not-create.db").exists()


def test_serve_runs_health_hunter_and_profile_observer_then_stops(tmp_path: Path, httpserver: HTTPServer) -> None:
    prime_radarr(httpserver)
    httpserver.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    httpserver.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = cli_env(tmp_path)
    env.update(WARDEN_METRICS_PORT=str(port), WARDEN_POLL_INTERVAL_SEC="0.1",
               WARDEN_RADARR_URL=httpserver.url_for(""), WARDEN_RADARR_API_KEY="test-key",
               WARDEN_PROFILES_DIRECTORY=str(EXAMPLES), WARDEN_PROFILES_INTERVAL_SEC="0.1")
    logfile = tmp_path / "server.log"
    with logfile.open("w") as stream:
        proc = subprocess.Popen([sys.executable, "-m", "warden", "serve"], cwd=tmp_path,
                                env=env, stdout=stream, stderr=subprocess.STDOUT, text=True)
        handle = WardenHandle(f"http://127.0.0.1:{port}", proc, logfile)
        try:
            _wait_healthz(handle, timeout=15)
            assert poll_until(lambda: sample(scrape(handle), "warden_profiles_check_success", source="radarr") == 1)
            assert poll_until(lambda: any(request.path == "/api/v3/wanted/missing" for request, _ in httpserver.log))
            assert (tmp_path / "must-not-create.db").is_file()
            proc.send_signal(signal.SIGTERM)
            assert proc.wait(timeout=10) in (0, -signal.SIGTERM)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=5)
