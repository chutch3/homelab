import signal

from tests.integration.conftest import (
    commands, prime_radarr, prime_sonarr, poll_until, scrape,
)


class TestWardenBootAndHunt:
    def test_boots_serves_metrics_hunts_and_stops(self, launch, radarr_server, sonarr_server):
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
