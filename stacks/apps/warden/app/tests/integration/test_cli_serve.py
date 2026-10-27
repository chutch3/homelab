from __future__ import annotations

import json
import os
import signal
import subprocess
from copy import deepcopy
from collections.abc import Callable
from pathlib import Path

from pytest_httpserver import HTTPServer
import yaml

from tests.profile_data import REMOTE_FORMAT, REMOTE_PROFILE
from tests.integration.conftest import WardenHandle, commit, git, start_observer, stop_server, dump_catalog, profile_events

import pytest

from tests.integration.conftest import (
    commands, down, prime_prowlarr, prime_radarr, prime_sonarr, poll_until, sample, scrape,
)

pytestmark = pytest.mark.integration

# Prowlarr fixtures mirroring the live API shapes (from the retired client tests).
APPS = [
    {"name": "Radarr", "implementation": "Radarr", "tags": [1],
     "fields": [{"name": "syncCategories", "value": [2000, 2040]}]},
]
# Two indexers with different per-day limits: the budget must bind to the SMALLER (20),
# since a hunt queries every indexer (regression guard for max-vs-min).
INDEXERS = [
    {"id": 7, "name": "YTS", "enable": True, "protocol": "torrent", "tags": [1],
     "capabilities": {"categories": [{"id": 2000, "name": "Movies"}, {"id": 2040, "name": "HD"}]},
     "fields": [{"name": "baseSettings.queryLimit", "value": 50},
                {"name": "baseSettings.limitsUnit", "value": 0}]},
    {"id": 8, "name": "SmallIdx", "enable": True, "protocol": "torrent", "tags": [1],
     "capabilities": {"categories": [{"id": 2000, "name": "Movies"}]},
     "fields": [{"name": "baseSettings.queryLimit", "value": 20},
                {"name": "baseSettings.limitsUnit", "value": 0}]},
]


def _env(radarr_server, sonarr_server, **extra):
    return {
        "WARDEN_RADARR_URL": radarr_server.url_for("").rstrip("/"), "WARDEN_RADARR_API_KEY": "rk",
        "WARDEN_SONARR_URL": sonarr_server.url_for("").rstrip("/"), "WARDEN_SONARR_API_KEY": "sk",
        **extra,
    }


def test_boots_serves_metrics_hunts_and_stops(launch, radarr_server, sonarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune"), (12, "Heat")])
    prime_sonarr(sonarr_server, missing=[])  # sonarr present but nothing to hunt

    warden = launch(
        WARDEN_RADARR_URL=radarr_server.url_for("").rstrip("/"),
        WARDEN_RADARR_API_KEY="rk",
        WARDEN_SONARR_URL=sonarr_server.url_for("").rstrip("/"),
        WARDEN_SONARR_API_KEY="sk",
    )

    # /metrics is served and exposes build info
    assert "warden_build_info" in scrape(warden)

    # the real loop issues a MoviesSearch against the radarr fake
    issued = poll_until(lambda: commands(radarr_server))
    assert issued, "warden never issued a search command"
    body = issued[0]
    assert body["name"] == "MoviesSearch"
    # pacing allows ~1/tick; assert it searched from the primed set (head first)
    assert body["movieIds"], "empty search"
    assert set(body["movieIds"]) <= {11, 12}
    assert 11 in body["movieIds"]

    # graceful shutdown
    warden.proc.send_signal(signal.SIGTERM)
    warden.proc.wait(timeout=15)
    assert warden.proc.returncode == 0


def test_sonarr_uses_episode_search_command(launch, radarr_server, sonarr_server):
    prime_radarr(radarr_server, missing=[])
    prime_sonarr(sonarr_server, missing=[(5, "S01E05"), (6, "S01E06")])
    launch(**_env(radarr_server, sonarr_server))
    issued = poll_until(lambda: commands(sonarr_server))
    assert issued and issued[0]["name"] == "EpisodeSearch"
    # pacing allows ~1/tick; assert it searched from the primed set (head first)
    assert set(issued[0]["episodeIds"]) <= {5, 6}
    assert 5 in issued[0]["episodeIds"]


def test_blocked_source_issues_no_search(launch, radarr_server, sonarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune")])
    prime_sonarr(sonarr_server, missing=[])
    warden = launch(**_env(radarr_server, sonarr_server), WARDEN_FALLBACK_SEARCHES_PER_DAY="0")
    blocked = poll_until(lambda: sample(scrape(warden), "warden_blocked", source="radarr") == 1.0)
    assert blocked
    assert commands(radarr_server) == []
    assert sample(scrape(warden), "warden_paused_ticks_total", source="radarr") >= 1.0
    # janitor decoupled from the hunt-block: warden keeps ticking while blocked (last_tick advances)
    t1 = sample(scrape(warden), "warden_last_tick_timestamp_seconds")
    assert poll_until(lambda: (sample(scrape(warden), "warden_last_tick_timestamp_seconds") or 0) > t1,
                      timeout=10)


def test_prowlarr_provenance_metrics(launch, radarr_server, sonarr_server, prowlarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune")])
    prime_sonarr(sonarr_server, missing=[])
    prime_prowlarr(prowlarr_server, apps=APPS, indexers=INDEXERS)
    warden = launch(**_env(radarr_server, sonarr_server),
                    WARDEN_PROWLARR_URL=prowlarr_server.url_for("").rstrip("/"),
                    WARDEN_PROWLARR_API_KEY="pk")
    got = poll_until(lambda: sample(scrape(warden), "warden_quota_prowlarr", source="radarr") == 1.0)
    assert got
    text = scrape(warden)
    # budget binds to the most-constrained indexer (20), not the most-generous (50)
    assert sample(text, "warden_binding_query_limit", source="radarr") == 20.0
    assert sample(text, "warden_indexers_total", source="radarr") == 2.0


def test_fallback_provenance_metric(launch, radarr_server, sonarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune")])
    prime_sonarr(sonarr_server, missing=[])
    warden = launch(**_env(radarr_server, sonarr_server))  # no prowlarr
    # 0.0 is falsy, so poll on the equality predicate and assert the poll succeeded
    assert poll_until(lambda: sample(scrape(warden), "warden_quota_prowlarr", source="radarr") == 0.0)


def test_one_upstream_down_does_not_block_the_other(launch, radarr_server, sonarr_server):
    down(radarr_server)
    prime_sonarr(sonarr_server, missing=[(5, "S01E05")])
    warden = launch(**_env(radarr_server, sonarr_server))
    issued = poll_until(lambda: commands(sonarr_server))
    assert issued and issued[0]["name"] == "EpisodeSearch"
    assert sample(scrape(warden), "warden_instance_up", source="radarr") == 0.0


def test_prowlarr_down_falls_back_and_keeps_hunting(launch, radarr_server, sonarr_server, prowlarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune")])
    prime_sonarr(sonarr_server, missing=[])
    down(prowlarr_server)
    warden = launch(**_env(radarr_server, sonarr_server),
                    WARDEN_PROWLARR_URL=prowlarr_server.url_for("").rstrip("/"),
                    WARDEN_PROWLARR_API_KEY="pk",
                    WARDEN_PROWLARR_FALLBACK_ON_ERROR="true")
    issued = poll_until(lambda: commands(radarr_server))
    assert issued  # fell back to flat budget and still hunted
    assert sample(scrape(warden), "warden_prowlarr_up") == 0.0


def test_prowlarr_down_fallback_disabled_issues_no_search(launch, radarr_server, sonarr_server, prowlarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune")])
    prime_sonarr(sonarr_server, missing=[])
    down(prowlarr_server)
    warden = launch(**_env(radarr_server, sonarr_server),
                    WARDEN_PROWLARR_URL=prowlarr_server.url_for("").rstrip("/"),
                    WARDEN_PROWLARR_API_KEY="pk",
                    WARDEN_PROWLARR_FALLBACK_ON_ERROR="false")
    got = poll_until(lambda: sample(scrape(warden), "warden_prowlarr_up") == 0.0)
    assert got
    assert commands(radarr_server) == []


from tests.integration.conftest import deletes, stale_record  # noqa: E402


def test_stale_download_is_removed_and_blocklisted(launch, radarr_server, sonarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune")],
                 queue=[stale_record(11, 55, id_field="movieId")])
    prime_sonarr(sonarr_server, missing=[])
    warden = launch(**_env(radarr_server, sonarr_server))
    removed = poll_until(lambda: deletes(radarr_server))
    assert removed
    req = removed[0]
    assert req.path == "/api/v3/queue/55"
    assert req.query_string.decode() == "removeFromClient=true&blocklist=true"
    assert poll_until(lambda: (sample(scrape(warden), "warden_stale_removed_total",
                                      source="radarr", reason="stalled") or 0) >= 1.0)


def test_in_queue_item_is_not_searched(launch, radarr_server, sonarr_server):
    healthy = {"id": 60, "movieId": 11, "title": "Dune", "status": "downloading",
               "errorMessage": None, "added": "2026-06-18T00:00:00Z"}
    prime_radarr(radarr_server, missing=[(11, "Dune"), (13, "Other")], queue=[healthy])
    prime_sonarr(sonarr_server, missing=[])
    launch(**_env(radarr_server, sonarr_server))
    issued = poll_until(lambda: commands(radarr_server))
    assert issued
    for body in commands(radarr_server):
        assert 11 not in body.get("movieIds", [])     # in queue -> excluded
    searched = {i for body in commands(radarr_server) for i in body.get("movieIds", [])}
    assert 13 in searched                              # not in queue -> hunted


def test_sweep_disabled_keeps_exclusion_but_no_delete(launch, radarr_server, sonarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune"), (13, "Other")],
                 queue=[stale_record(11, 55, id_field="movieId")])
    prime_sonarr(sonarr_server, missing=[])
    launch(**_env(radarr_server, sonarr_server), WARDEN_STALE_SWEEP_ENABLED="false")
    issued = poll_until(lambda: commands(radarr_server))
    assert issued
    assert deletes(radarr_server) == []                # nothing removed
    for body in commands(radarr_server):
        assert 11 not in body.get("movieIds", [])      # still excluded
    searched = {i for body in commands(radarr_server) for i in body.get("movieIds", [])}
    assert 13 in searched


def test_searches_least_recently_searched_first(launch, radarr_server, sonarr_server):
    # 1 searched recently, 2 never, 3 searched long ago -> LRS order is [2, 3, 1],
    # so the never-searched item (2) must be hunted first, not the recent head (1).
    prime_radarr(radarr_server, missing=[
        {"id": 1, "title": "recent", "lastSearchTime": "2026-06-18T12:00:00Z"},
        {"id": 2, "title": "never"},
        {"id": 3, "title": "old", "lastSearchTime": "2026-05-01T00:00:00Z"},
    ])
    prime_sonarr(sonarr_server, missing=[])
    launch(**_env(radarr_server, sonarr_server))
    issued = poll_until(lambda: commands(radarr_server))
    assert issued
    assert issued[0]["movieIds"][0] == 2          # never-searched hunted first, not the recent head (1)


def test_no_progress_download_is_removed(launch, radarr_server, sonarr_server):
    # constant sizeleft across ticks + window=0 -> flagged no-progress on the second tick
    stuck = {"id": 55, "movieId": 11, "title": "stuck", "status": "downloading",
             "errorMessage": None, "added": "2026-06-15T00:00:00Z",
             "downloadId": "DID1", "size": 2000, "sizeleft": 1000}
    prime_radarr(radarr_server, missing=[], queue=[stuck])
    prime_sonarr(sonarr_server, missing=[])
    warden = launch(**_env(radarr_server, sonarr_server), WARDEN_STALE_NO_PROGRESS_HOURS="0")
    removed = poll_until(lambda: deletes(radarr_server), timeout=20)
    assert removed and removed[0].path == "/api/v3/queue/55"
    assert removed[0].query_string.decode() == "removeFromClient=true&blocklist=true"
    assert poll_until(lambda: (sample(scrape(warden), "warden_stale_removed_total",
                                      source="radarr", reason="no_progress") or 0) >= 1.0, timeout=20)


def test_progressing_download_is_not_removed(launch, radarr_server, sonarr_server):
    from tests.integration.conftest import prime_progressing, queue_fetches
    # sizeleft drops 1 GB/fetch (>> 100 MB min) from a huge start -> always progressing, never stale
    prime_progressing(radarr_server, queue_id=66, remote_id=11, id_field="movieId",
                      start_left=10_000_000_000_000, step=1_000_000_000)
    prime_sonarr(sonarr_server, missing=[])
    launch(**_env(radarr_server, sonarr_server),
           WARDEN_STALE_NO_PROGRESS_HOURS="0", WARDEN_STALE_JITTER_TOLERANCE_MB="100")
    # let several ticks evaluate it, then assert it was never removed
    assert poll_until(lambda: queue_fetches(radarr_server) >= 4, timeout=20)
    assert deletes(radarr_server) == []


def test_queued_download_is_not_removed(launch, radarr_server, sonarr_server):
    from tests.integration.conftest import queue_fetches
    # an item merely waiting in a backlogged client (status "queued") has a flat sizeleft
    # by design — even with a 0h window it must never be flagged no-progress / blocklisted.
    waiting = {"id": 77, "movieId": 11, "title": "waiting", "status": "queued",
               "errorMessage": None, "added": "2026-06-15T00:00:00Z",
               "downloadId": "DID2", "size": 2000, "sizeleft": 1000}
    prime_radarr(radarr_server, missing=[], queue=[waiting])
    prime_sonarr(sonarr_server, missing=[])
    launch(**_env(radarr_server, sonarr_server), WARDEN_STALE_NO_PROGRESS_HOURS="0")
    assert poll_until(lambda: queue_fetches(radarr_server) >= 4, timeout=20)
    assert deletes(radarr_server) == []


def test_grab_efficacy_records_hits_and_misses(launch, radarr_server, sonarr_server):
    # radarr's item is "grabbed" (history returns it) -> hit; sonarr's never is -> miss after
    # the resolve window. One item per instance so the pacer (≈1/tick) searches each every tick.
    prime_radarr(radarr_server, missing=[(101, "Hit Movie")], grab_ids=[101])
    prime_sonarr(sonarr_server, missing=[(201, "Miss Show")], grab_ids=[])
    warden = launch(**_env(radarr_server, sonarr_server), WARDEN_EFFICACY_RESOLVE_MINUTES="0.005")

    hit = poll_until(lambda: sample(scrape(warden), "warden_search_hit_total",
                                    source="radarr", indexer="TestIndexer"), timeout=20)
    assert hit and hit >= 1.0, "warden never attributed a grab to its search"

    miss = poll_until(lambda: sample(scrape(warden), "warden_search_miss_total", source="sonarr"),
                      timeout=20)
    assert miss and miss >= 1.0, "warden never recorded a miss for the never-grabbed item"


GB = 1_000_000_000


def test_low_disk_pauses_hunting_but_keeps_janitor(launch, radarr_server, sonarr_server):
    # only 5 GB free, floor is 50 GB -> hunting is space-blocked, but the loop keeps
    # ticking (janitor is decoupled from the space gate, same as the quota gate).
    prime_radarr(radarr_server, missing=[(11, "Dune"), (12, "Heat")], free_space=5 * GB)
    prime_sonarr(sonarr_server, missing=[])
    warden = launch(**_env(radarr_server, sonarr_server), WARDEN_MIN_FREE_GB="50")

    blocked = poll_until(lambda: sample(scrape(warden), "warden_space_blocked", source="radarr") == 1.0)
    assert blocked
    assert commands(radarr_server) == []
    assert sample(scrape(warden), "warden_space_paused_ticks_total", source="radarr") >= 1.0
    # loop keeps ticking while space-blocked (last_tick advances)
    t1 = sample(scrape(warden), "warden_last_tick_timestamp_seconds")
    assert poll_until(lambda: (sample(scrape(warden), "warden_last_tick_timestamp_seconds") or 0) > t1,
                      timeout=10)


def test_in_flight_queue_counts_against_headroom(launch, radarr_server, sonarr_server):
    # 100 GB free looks fine against a 50 GB floor, but 80 GB is still downloading in the
    # queue -> projected headroom (20 GB) is under the floor, so hunting is blocked.
    huge = {"id": 90, "movieId": 11, "title": "big", "status": "downloading",
            "errorMessage": None, "added": "2026-06-18T00:00:00Z",
            "downloadId": "DL90", "size": 80 * GB, "sizeleft": 80 * GB}
    prime_radarr(radarr_server, missing=[(11, "Dune"), (13, "Other")], queue=[huge],
                 free_space=100 * GB)
    prime_sonarr(sonarr_server, missing=[])
    warden = launch(**_env(radarr_server, sonarr_server), WARDEN_MIN_FREE_GB="50")

    blocked = poll_until(lambda: sample(scrape(warden), "warden_space_blocked", source="radarr") == 1.0)
    assert blocked
    assert commands(radarr_server) == []


def test_ample_disk_still_hunts(launch, radarr_server, sonarr_server):
    prime_radarr(radarr_server, missing=[(11, "Dune")], free_space=500 * GB)
    prime_sonarr(sonarr_server, missing=[])
    warden = launch(**_env(radarr_server, sonarr_server), WARDEN_MIN_FREE_GB="50")
    issued = poll_until(lambda: commands(radarr_server))
    assert issued and issued[0]["name"] == "MoviesSearch"
    text = scrape(warden)
    assert sample(text, "warden_space_blocked", source="radarr") == 0.0
    assert sample(text, "warden_free_bytes", source="radarr") == float(500 * GB)


def test_unfindable_item_is_backed_off(launch, radarr_server, sonarr_server):
    # a never-grabbed item that misses (threshold=1) earns a cooldown and drops out of hunting.
    prime_radarr(radarr_server, missing=[])
    prime_sonarr(sonarr_server, missing=[(201, "Ghost Show")], grab_ids=[])
    warden = launch(**_env(radarr_server, sonarr_server),
                    WARDEN_EFFICACY_RESOLVE_MINUTES="0.005", WARDEN_BACKOFF_MISS_THRESHOLD="1")

    active = poll_until(lambda: sample(scrape(warden), "warden_backoff_active", source="sonarr"),
                        timeout=20)
    assert active and active >= 1.0, "warden never backed off the unfindable item"


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
    dump_catalog(radarr_server, output_directory)
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


def test_serve_observes_immutable_git_revision_without_rewriting_unchanged_cache(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    warden = start_observer(repository, radarr_server, launch)
    assert poll_until(lambda: profile_events(warden))
    event = profile_events(warden)[-1]
    assert event['commit'] == git(repository, 'rev-parse', 'HEAD')
    assert event['profiles'] == ['HD']
    assert event['changes'] == []
    cache = repository.parent / 'cache'
    before = {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in cache.rglob('*') if p.is_file()}
    count = len(profile_events(warden))
    assert poll_until(lambda: len(profile_events(warden)) > count)
    assert profile_events(warden)[-1]['commit'] == event['commit']
    assert {p: (p.stat().st_mtime_ns, p.read_bytes()) for p in before} == before


def test_serve_preserves_valid_git_cache_when_candidate_is_invalid(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    warden = start_observer(repository, radarr_server, launch)
    assert poll_until(lambda: profile_events(warden))
    good = profile_events(warden)[-1]['commit']
    (repository / 'radarr/profiles/HD.yml').write_text('invalid: true\n')
    commit(repository, 'broken catalog')
    assert poll_until(lambda: sample(scrape(warden), 'warden_profiles_check_success', source='radarr') == 0)
    snapshots = list((repository.parent / 'cache').glob('snapshot-*'))
    assert len(snapshots) == 1
    assert git(snapshots[0], 'rev-parse', 'HEAD') == good
    assert profile_events(warden)[-1]['commit'] == good


def test_serve_honors_commit_pin_and_catalog_subdirectory(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    nested = repository / 'catalog'
    nested.mkdir()
    (repository / 'radarr').rename(nested / 'radarr')
    pinned = commit(repository, 'nested catalog')
    path = nested / 'radarr/profiles/HD.yml'
    path.write_text(path.read_text().replace('Preferred: 100', 'Preferred: 250'))
    commit(repository, 'later revision')
    warden = start_observer(repository, radarr_server, launch, WARDEN_PROFILES_REF=pinned, WARDEN_PROFILES_PATH='catalog')
    assert poll_until(lambda: profile_events(warden))
    assert profile_events(warden)[-1]['commit'] == pinned
    assert profile_events(warden)[-1]['changes'] == []
    assert sample(scrape(warden), 'warden_profiles_drift_resources', source='radarr', kind='profile') == 0


def test_serve_resolves_annotated_tag_to_commit(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    git(repository, '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'tag', '-a', 'v1', '-m', 'catalog v1')
    warden = start_observer(repository, radarr_server, launch, WARDEN_PROFILES_REF='v1')
    assert poll_until(lambda: profile_events(warden))
    assert profile_events(warden)[-1]['commit'] == git(repository, 'rev-parse', 'HEAD')


def test_serve_rejects_oversized_git_candidate_and_cleans_it(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    (repository / 'large.bin').write_bytes(bytes(range(256)) * 4096)
    commit(repository, 'oversized worktree')
    warden = start_observer(repository, radarr_server, launch, WARDEN_PROFILES_CACHE_MAX_BYTES='262144')
    assert poll_until(lambda: 'profile_repository_error' in warden.logfile.read_text())
    stop_server(warden)
    assert list((repository.parent / 'cache').glob('snapshot-*')) == []
    assert not profile_events(warden)
    assert not any(request.path == '/api/v3/qualityprofile' for request, _ in radarr_server.log)


@pytest.mark.parametrize('kind', ['user_files', 'symlink'])
def test_serve_refuses_unsafe_cache_without_modifying_existing_data(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle], kind: str,
) -> None:
    cache = repository.parent / 'cache'
    if kind == 'user_files':
        cache.mkdir()
        (cache / 'keep.txt').write_text('user data')
    else:
        cache.symlink_to(repository, target_is_directory=True)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in cache.rglob('*') if p.is_file()}
    warden = start_observer(repository, radarr_server, launch)
    assert poll_until(lambda: 'profile_repository_error' in warden.logfile.read_text())
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before
    assert sample(scrape(warden), 'warden_profiles_check_success', source='radarr') == 0
    assert not any(request.path == '/api/v3/qualityprofile' for request, _ in radarr_server.log)
    assert git(repository, 'status', '--porcelain') == ''


def test_serve_restart_rebuilds_disposable_cache(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    first = start_observer(repository, radarr_server, launch)
    assert poll_until(lambda: profile_events(first))
    revision = profile_events(first)[-1]['commit']
    stop_server(first)
    previous = set((repository.parent / 'cache').glob('snapshot-*'))
    restarted = start_observer(repository, radarr_server, launch)
    assert poll_until(lambda: profile_events(restarted))
    assert profile_events(restarted)[-1]['commit'] == revision
    snapshots = set((repository.parent / 'cache').glob('snapshot-*'))
    assert len(snapshots) == 1
    assert not snapshots & previous


def test_serve_timeout_kills_git_and_hunting_continues(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle], tmp_path: Path,
) -> None:
    executable = tmp_path / 'git'
    pidfile = tmp_path / 'pid'
    executable.write_text('#!/usr/bin/env bash\nset -euo pipefail\necho "$$" > "$WARDEN_TEST_PIDFILE"\nexec sleep 30\n')
    executable.chmod(0o755)
    warden = start_observer(
        repository, radarr_server, launch, PATH=f"{tmp_path}:{os.environ['PATH']}",
        WARDEN_TEST_PIDFILE=str(pidfile), WARDEN_PROFILES_TIMEOUT_SEC='0.5', WARDEN_PROFILES_INTERVAL_SEC='30',
    )
    assert poll_until(lambda: pidfile.is_file())
    assert poll_until(lambda: 'profile_cycle_timeout' in warden.logfile.read_text() or 'profile_repository_error' in warden.logfile.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(int(pidfile.read_text()), 0)
    assert sample(scrape(warden), 'warden_profiles_check_success', source='radarr') == 0
    tick = sample(scrape(warden), 'warden_last_tick_timestamp_seconds')
    assert poll_until(lambda: (sample(scrape(warden), 'warden_last_tick_timestamp_seconds') or 0) > tick)


def test_serve_directory_revision_tracks_content_without_writes(
    output_directory: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    dump_catalog(radarr_server, output_directory)
    before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in output_directory.rglob('*') if p.is_file()}
    warden = start_observer(output_directory, radarr_server, launch,
                            WARDEN_PROFILES_REPO='', WARDEN_PROFILES_DIRECTORY=str(output_directory))
    assert poll_until(lambda: profile_events(warden))
    first = profile_events(warden)[-1]
    assert first['commit'].startswith('directory:')
    count = len(profile_events(warden))
    assert poll_until(lambda: len(profile_events(warden)) > count)
    assert profile_events(warden)[-1]['commit'] == first['commit']
    assert {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in before} == before
    path = output_directory / 'radarr/profiles/HD.yml'
    path.write_text(path.read_text().replace('Preferred: 100', 'Preferred: 250'))
    assert poll_until(lambda: profile_events(warden)[-1]['commit'] != first['commit'])
    assert profile_events(warden)[-1]['changes'] == [
        {'kind': 'profile', 'name': 'HD', 'field': 'custom_format_scores.Preferred', 'current': 100, 'desired': 250},
    ]


@pytest.mark.parametrize('problem', ['byte_limit', 'symlinked_parent'])
def test_serve_rejects_invalid_directory_before_arr_reads(
    output_directory: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle], problem: str,
) -> None:
    dump_catalog(radarr_server, output_directory)
    radarr_server.clear_log()
    directory = output_directory
    env = {}
    if problem == 'byte_limit':
        env['WARDEN_PROFILES_CACHE_MAX_BYTES'] = '20'
    else:
        link = output_directory.parent / 'alias'
        link.symlink_to(output_directory.parent, target_is_directory=True)
        directory = link / output_directory.name
    warden = start_observer(output_directory, radarr_server, launch,
                            WARDEN_PROFILES_REPO='', WARDEN_PROFILES_DIRECTORY=str(directory), **env)
    assert poll_until(lambda: 'profile_repository_error' in warden.logfile.read_text())
    assert sample(scrape(warden), 'warden_profiles_check_success', source='radarr') == 0
    assert not any(request.path == '/api/v3/qualityprofile' for request, _ in radarr_server.log)
    assert not (output_directory.parent / 'cache').exists()


def test_serve_disabled_source_has_no_success_baseline_or_profile_reads(
    repository: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    warden = start_observer(repository, radarr_server, launch, WARDEN_RADARR_PROFILES='[]')
    metrics = scrape(warden)
    assert sample(metrics, 'warden_profiles_enabled', source='radarr') == 0
    assert sample(metrics, 'warden_profiles_last_successful_check_timestamp_seconds', source='radarr') == 0
    assert not any(request.path == '/api/v3/qualityprofile' for request, _ in radarr_server.log)
    assert not (repository.parent / 'cache').exists()


def test_serve_metrics_preserve_drift_and_freshness_on_failure_then_clear_on_recovery(
    output_directory: Path, radarr_server: HTTPServer, launch: Callable[..., WardenHandle],
) -> None:
    dump_catalog(radarr_server, output_directory)
    path = output_directory / 'radarr/profiles/HD.yml'
    original = path.read_text()
    path.write_text(original.replace('Preferred: 100', 'Preferred: 250'))
    second = output_directory / 'radarr/profiles/HD2.yml'
    second_original = yaml.safe_load(original)
    second_original['quality_profiles'][0]['name'] = 'HD2'
    second.write_text(yaml.safe_dump(second_original).replace('Preferred: 100', 'Preferred: 250'))
    format_path = output_directory / 'radarr/custom_formats/Preferred.json'
    original_format = format_path.read_text()
    data = json.loads(original_format)
    data['specifications'][0]['fields']['value'] = 'New pattern'
    format_path.write_text(json.dumps(data))
    radarr_server.clear_all_handlers()
    remote_second = {**deepcopy(REMOTE_PROFILE), 'id': 46, 'name': 'HD2'}
    other = {**deepcopy(REMOTE_PROFILE), 'id': 47, 'name': 'Other'}
    prime_radarr(radarr_server)
    radarr_server.expect_request('/api/v3/qualityprofile', method='GET').respond_with_json([REMOTE_PROFILE, remote_second, other])
    radarr_server.expect_request('/api/v3/customformat', method='GET').respond_with_json([REMOTE_FORMAT])
    warden = launch(
        WARDEN_RADARR_URL=radarr_server.url_for(''), WARDEN_RADARR_API_KEY='test-key',
        WARDEN_PROFILES_DIRECTORY=str(output_directory), WARDEN_PROFILES_INTERVAL_SEC='0.2',
    )
    assert poll_until(lambda: sample(scrape(warden), 'warden_profiles_check_success', source='radarr') == 1)
    metrics = scrape(warden)
    since = sample(metrics, 'warden_profiles_drift_since_timestamp_seconds', source='radarr')
    last_good = sample(metrics, 'warden_profiles_last_successful_check_timestamp_seconds', source='radarr')
    assert since > 0
    assert sample(metrics, 'warden_profiles_drift_resources', source='radarr', kind='profile') == 2
    assert sample(metrics, 'warden_profiles_drift_resources', source='radarr', kind='custom_format') == 1
    assert sample(metrics, 'warden_profiles_conflicts', source='radarr') == 1
    path.write_text(original.replace('Preferred: 100', 'Preferred: 350'))
    assert poll_until(lambda: sample(scrape(warden), 'warden_profiles_last_successful_check_timestamp_seconds', source='radarr') > last_good)
    assert sample(scrape(warden), 'warden_profiles_drift_since_timestamp_seconds', source='radarr') == since
    path.write_text('invalid: true\n')
    assert poll_until(lambda: sample(scrape(warden), 'warden_profiles_check_success', source='radarr') == 0)
    failed = scrape(warden)
    freshness = sample(failed, 'warden_profiles_last_successful_check_timestamp_seconds', source='radarr')
    cycles = sample(failed, 'warden_profiles_cycle_duration_seconds_count')
    assert poll_until(lambda: sample(scrape(warden), 'warden_profiles_cycle_duration_seconds_count') > cycles)
    metrics = scrape(warden)
    assert sample(metrics, 'warden_profiles_last_successful_check_timestamp_seconds', source='radarr') == freshness
    assert sample(metrics, 'warden_profiles_drift_since_timestamp_seconds', source='radarr') == since
    assert sample(metrics, 'warden_profiles_drift_resources', source='radarr', kind='profile') == 2
    assert sample(metrics, 'warden_profiles_drift_resources', source='radarr', kind='custom_format') == 1
    assert sample(metrics, 'warden_profiles_conflicts', source='radarr') == 1
    path.write_text(original)
    second.write_text(yaml.safe_dump(second_original))
    format_path.write_text(original_format)
    assert poll_until(lambda: sample(scrape(warden), 'warden_profiles_check_success', source='radarr') == 1
                      and sample(scrape(warden), 'warden_profiles_drift_since_timestamp_seconds', source='radarr') == 0)
    metrics = scrape(warden)
    assert sample(metrics, 'warden_profiles_drift_resources', source='radarr', kind='profile') == 0
    assert sample(metrics, 'warden_profiles_drift_resources', source='radarr', kind='custom_format') == 0
    assert sample(metrics, 'warden_profiles_conflicts', source='radarr') == 0
    assert all(request.method == 'GET' for request, _ in radarr_server.log)
