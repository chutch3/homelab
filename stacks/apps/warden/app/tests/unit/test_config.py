from warden.config import Config
from warden.models import ArrType


class TestConfig:
    def test_discovers_instances_from_env(self, monkeypatch):
        monkeypatch.setenv("WARDEN_RADARR_URL", "http://radarr:7878/")
        monkeypatch.setenv("WARDEN_RADARR_API_KEY", "rk")
        monkeypatch.setenv("WARDEN_SONARR_URL", "http://sonarr:8989")
        monkeypatch.setenv("WARDEN_SONARR_API_KEY", "sk")
        cfg = Config.from_env()
        assert [(i.name, i.type, i.url, i.api_key) for i in cfg.instances] == [
            ("radarr", ArrType.RADARR, "http://radarr:7878", "rk"),
            ("sonarr", ArrType.SONARR, "http://sonarr:8989", "sk"),
        ]

    def test_instance_skipped_when_key_missing(self, monkeypatch):
        monkeypatch.delenv("WARDEN_SONARR_URL", raising=False)
        monkeypatch.delenv("WARDEN_SONARR_API_KEY", raising=False)
        monkeypatch.setenv("WARDEN_RADARR_URL", "http://radarr:7878")
        monkeypatch.delenv("WARDEN_RADARR_API_KEY", raising=False)  # url without key -> skip
        cfg = Config.from_env()
        assert cfg.instances == ()

    def test_tuning_defaults_when_env_absent(self, monkeypatch):
        for var in ("WARDEN_RADARR_URL", "WARDEN_RADARR_API_KEY", "WARDEN_SONARR_URL",
                    "WARDEN_SONARR_API_KEY",
                    "WARDEN_RESERVE_PCT", "WARDEN_FALLBACK_SEARCHES_PER_DAY",
                    "WARDEN_RESET_AT_LOCAL", "WARDEN_INCLUDE_CUTOFF_UNMET",
                    "WARDEN_POLL_INTERVAL_SEC", "WARDEN_DB_URL", "WARDEN_DB_PATH"):
            monkeypatch.delenv(var, raising=False)
        cfg = Config.from_env()
        assert cfg.instances == ()
        assert cfg.reserve_pct == 20
        assert cfg.fallback_searches_per_day == 200
        assert cfg.reset_at_local == "00:00"
        assert cfg.include_cutoff_unmet is True
        assert cfg.poll_interval_sec == 300
        assert cfg.db_url == "sqlite:////state/warden.db"
        assert cfg.metrics_port == 9090

    def test_tuning_overridden_from_env(self, monkeypatch):
        monkeypatch.setenv("WARDEN_RESERVE_PCT", "10")
        monkeypatch.setenv("WARDEN_FALLBACK_SEARCHES_PER_DAY", "50")
        monkeypatch.setenv("WARDEN_RESET_AT_LOCAL", "03:30")
        monkeypatch.setenv("WARDEN_INCLUDE_CUTOFF_UNMET", "false")
        monkeypatch.setenv("WARDEN_POLL_INTERVAL_SEC", "120")
        cfg = Config.from_env()
        assert cfg.reserve_pct == 10
        assert cfg.fallback_searches_per_day == 50
        assert cfg.reset_at_local == "03:30"
        assert cfg.include_cutoff_unmet is False
        assert cfg.poll_interval_sec == 120

    def test_prowlarr_and_default_cap_from_env(self, monkeypatch):
        monkeypatch.setenv("WARDEN_PROWLARR_URL", "http://prowlarr:9696/")
        monkeypatch.setenv("WARDEN_PROWLARR_API_KEY", "pk")
        monkeypatch.setenv("WARDEN_DEFAULT_QUERY_LIMIT", "100")
        cfg = Config.from_env()
        assert cfg.prowlarr_url == "http://prowlarr:9696"
        assert cfg.prowlarr_api_key == "pk"
        assert cfg.default_query_limit == 100

    def test_prowlarr_defaults_empty(self, monkeypatch):
        for v in ("WARDEN_PROWLARR_URL", "WARDEN_PROWLARR_API_KEY", "WARDEN_DEFAULT_QUERY_LIMIT"):
            monkeypatch.delenv(v, raising=False)
        cfg = Config.from_env()
        assert cfg.prowlarr_url == ""
        assert cfg.prowlarr_api_key == ""
        assert cfg.default_query_limit == 100

    def test_tz_prefers_warden_tz_then_tz_then_utc(self, monkeypatch):
        monkeypatch.delenv("WARDEN_TZ", raising=False)
        monkeypatch.delenv("TZ", raising=False)
        assert Config.from_env().tz == "UTC"
        monkeypatch.setenv("TZ", "America/New_York")
        assert Config.from_env().tz == "America/New_York"
        monkeypatch.setenv("WARDEN_TZ", "Europe/London")
        assert Config.from_env().tz == "Europe/London"

    def test_prowlarr_fallback_default_true_and_overridable(self, monkeypatch):
        monkeypatch.delenv("WARDEN_PROWLARR_FALLBACK_ON_ERROR", raising=False)
        assert Config.from_env().prowlarr_fallback_on_error is True
        monkeypatch.setenv("WARDEN_PROWLARR_FALLBACK_ON_ERROR", "false")
        assert Config.from_env().prowlarr_fallback_on_error is False


class TestStaleConfig:
    def test_stale_defaults(self, monkeypatch):
        for v in ("WARDEN_STALE_SWEEP_ENABLED", "WARDEN_STALE_GRACE_HOURS",
                  "WARDEN_STALE_MAX_REMOVALS_PER_TICK", "WARDEN_STALE_MASS_FRACTION",
                  "WARDEN_STALE_MIN_QUEUE_FOR_GUARD", "WARDEN_STALE_NO_PROGRESS_ENABLED",
                  "WARDEN_STALE_NO_PROGRESS_HOURS", "WARDEN_STALE_JITTER_TOLERANCE_MB"):
            monkeypatch.delenv(v, raising=False)
        cfg = Config.from_env()
        assert cfg.stale_sweep_enabled is True
        assert cfg.stale_grace_hours == 48.0
        assert cfg.stale_max_removals_per_tick == 5
        assert cfg.stale_mass_fraction == 0.5
        assert cfg.stale_min_queue_for_guard == 3
        assert cfg.stale_no_progress_enabled is True
        assert cfg.stale_no_progress_hours == 12.0
        assert cfg.stale_jitter_tolerance_mb == 0

    def test_stale_overrides(self, monkeypatch):
        monkeypatch.setenv("WARDEN_STALE_SWEEP_ENABLED", "false")
        monkeypatch.setenv("WARDEN_STALE_GRACE_HOURS", "12")
        monkeypatch.setenv("WARDEN_STALE_MAX_REMOVALS_PER_TICK", "2")
        cfg = Config.from_env()
        assert cfg.stale_sweep_enabled is False
        assert cfg.stale_grace_hours == 12.0
        assert cfg.stale_max_removals_per_tick == 2
