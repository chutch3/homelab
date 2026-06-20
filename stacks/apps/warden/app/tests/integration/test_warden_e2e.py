import os
import signal

import pytest

from tests.integration.conftest import (
    commands, down, prime_prowlarr, prime_radarr, prime_sonarr, poll_until, sample, scrape,
)

pytestmark = pytest.mark.skipif(os.getenv("WARDEN_INTEGRATION") != "1", reason="integration gated")

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
           WARDEN_STALE_NO_PROGRESS_HOURS="0", WARDEN_STALE_MIN_PROGRESS_MB="100")
    # let several ticks evaluate it, then assert it was never removed
    assert poll_until(lambda: queue_fetches(radarr_server) >= 4, timeout=20)
    assert deletes(radarr_server) == []
