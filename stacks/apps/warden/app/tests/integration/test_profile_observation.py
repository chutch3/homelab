from __future__ import annotations

import signal
import subprocess
from collections.abc import Callable, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from pytest_httpserver import HTTPServer

from tests.integration.conftest import WardenHandle, poll_until, prime_radarr, sample, scrape
from tests.integration.test_profile_dump import REMOTE_FORMAT, REMOTE_PROFILE
from tests.integration.test_profile_dump import output_directory
from warden.profiles.catalog_io import write_catalog
from warden.profiles.export import export_documents


pytestmark = pytest.mark.integration


def git(directory: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(directory), *args], capture_output=True, text=True, check=True, timeout=15,
    )
    return result.stdout.strip()


def commit(directory: Path, message: str) -> str:
    git(directory, "add", ".")
    git(directory, "-c", "user.name=Test", "-c", "user.email=test@example.invalid", "commit", "-m", message)
    return git(directory, "rev-parse", "HEAD")


@pytest.fixture()
def repository() -> Iterator[Path]:
    with TemporaryDirectory(prefix="warden-observe-", dir="/dev/shm") as directory:
        root = Path(directory) / "repo"
        write_catalog(root, export_documents("radarr", [REMOTE_PROFILE], [REMOTE_FORMAT], ()))
        git(root, "init", "-b", "main")
        commit(root, "initial catalog")
        yield root


def test_observes_git_changes_failures_and_recovery_without_arr_writes(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    prime_radarr(radarr_server)
    radarr_server.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    radarr_server.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    warden = launch(
        WARDEN_RADARR_URL=radarr_server.url_for(""), WARDEN_RADARR_API_KEY="test-key",
        WARDEN_SONARR_URL="", WARDEN_SONARR_API_KEY="", WARDEN_RADARR_PROFILES='["HD"]',
        WARDEN_PROFILES_REPO=str(repository), WARDEN_PROFILES_REF="main",
        WARDEN_PROFILES_CACHE_DIR=str(repository.parent / "cache"),
        WARDEN_PROFILES_INTERVAL_SEC="0.2", WARDEN_PROFILES_TIMEOUT_SEC="2",
    )
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 1)
    assert sample(scrape(warden), "warden_profiles_drift_resources", source="radarr", kind="profile") == 0
    path = repository / "radarr/profiles/HD.yml"
    original = path.read_text()
    path.write_text(original.replace("Preferred: 100", "Preferred: 250"))
    changed_commit = commit(repository, "change score")
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_drift_resources", source="radarr", kind="profile") == 1)
    assert changed_commit in warden.logfile.read_text()

    path.write_text("invalid: true\n")
    commit(repository, "invalid candidate")
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 0)
    assert sample(scrape(warden), "warden_profiles_drift_resources", source="radarr", kind="profile") == 1
    last_good = sample(scrape(warden), "warden_profiles_last_successful_check_timestamp_seconds", source="radarr")

    path.write_text(original)
    commit(repository, "restore score")
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 1
                      and sample(scrape(warden), "warden_profiles_drift_resources", source="radarr", kind="profile") == 0)
    assert sample(scrape(warden), "warden_profiles_last_successful_check_timestamp_seconds", source="radarr") > last_good

    repository.rename(repository.with_name("unavailable"))
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 0)
    last_tick = sample(scrape(warden), "warden_last_tick_timestamp_seconds")
    assert poll_until(lambda: (sample(scrape(warden), "warden_last_tick_timestamp_seconds") or 0) > last_tick)
    assert all(request.method == "GET" for request, _ in radarr_server.log)
    warden.proc.send_signal(signal.SIGTERM)
    warden.proc.wait(timeout=15)
    assert warden.proc.returncode == 0


@pytest.mark.parametrize("setting,value", [("WARDEN_PROFILES_MODE", "sync"), ("WARDEN_PROFILES_INTERVAL_SEC", "invalid")])
def test_invalid_profile_config_does_not_stop_hunting(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle], setting: str, value: str,
) -> None:
    prime_radarr(radarr_server)
    warden = launch(**{
        "WARDEN_RADARR_URL": radarr_server.url_for(""), "WARDEN_RADARR_API_KEY": "test-key",
        "WARDEN_PROFILES_REPO": str(repository), "WARDEN_PROFILES_CACHE_DIR": str(repository.parent / "cache"),
        setting: value,
    })
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 0)
    assert poll_until(lambda: (sample(scrape(warden), "warden_last_tick_timestamp_seconds") or 0) > 0)
    assert not (repository.parent / "cache").exists()


def test_directory_observation_tracks_edits_without_creating_git_or_cache(
    output_directory: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    write_catalog(output_directory, export_documents("radarr", [REMOTE_PROFILE], [REMOTE_FORMAT], ()))
    prime_radarr(radarr_server)
    radarr_server.expect_request("/api/v3/qualityprofile", method="GET").respond_with_json([REMOTE_PROFILE])
    radarr_server.expect_request("/api/v3/customformat", method="GET").respond_with_json([REMOTE_FORMAT])
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in output_directory.rglob('*') if p.is_file()}
    cache = output_directory.parent / "must-not-create-cache"
    warden = launch(
        WARDEN_RADARR_URL=radarr_server.url_for(""), WARDEN_RADARR_API_KEY="test-key",
        WARDEN_SONARR_URL="", WARDEN_SONARR_API_KEY="", WARDEN_PROFILES_REPO="",
        WARDEN_PROFILES_DIRECTORY=str(output_directory), WARDEN_PROFILES_CACHE_DIR=str(cache),
        WARDEN_PROFILES_INTERVAL_SEC="0.2", WARDEN_PROFILES_TIMEOUT_SEC="2",
    )
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 1)
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in output_directory.rglob('*') if p.is_file()} == before
    path = output_directory / "radarr/profiles/HD.yml"
    original = path.read_text()
    path.write_text(original.replace("Preferred: 100", "Preferred: 250"))
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_drift_resources", source="radarr", kind="profile") == 1)
    path.write_text("invalid: true\n")
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 0)
    assert sample(scrape(warden), "warden_profiles_drift_resources", source="radarr", kind="profile") == 1
    path.write_text(original)
    assert poll_until(lambda: sample(scrape(warden), "warden_profiles_check_success", source="radarr") == 1
                      and sample(scrape(warden), "warden_profiles_drift_resources", source="radarr", kind="profile") == 0)
    assert not cache.exists()
    assert not (output_directory / ".git").exists()
    assert "directory:" in warden.logfile.read_text()
    assert all(request.method == "GET" for request, _ in radarr_server.log)
