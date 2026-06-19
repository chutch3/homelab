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
INDEXERS = [
    {"id": 7, "name": "YTS", "enable": True, "protocol": "torrent", "tags": [1],
     "capabilities": {"categories": [{"id": 2000, "name": "Movies"}, {"id": 2040, "name": "HD"}]},
     "fields": [{"name": "baseSettings.queryLimit", "value": 50},
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
    assert sample(text, "warden_binding_query_limit", source="radarr") == 50.0
    assert sample(text, "warden_indexers_total", source="radarr") == 1.0


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
