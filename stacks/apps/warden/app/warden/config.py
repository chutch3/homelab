from __future__ import annotations

import os
from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from warden.models import ArrType, InstanceConfig


def _env_bool(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _min_free_bytes_from_env(env: Mapping[str, str]) -> int:
    """Space-guard floor from WARDEN_MIN_FREE_GB (GB -> bytes, decimal). Unset or empty
    means the guard is disabled (0 bytes); there is no baked-in default."""
    raw = env.get("WARDEN_MIN_FREE_GB", "").strip()
    if not raw:
        return 0
    return int(float(raw) * 1_000_000_000)


def _instances_from_env(env: Mapping[str, str]) -> Iterator[InstanceConfig]:
    """Discover configured *arr instances from env vars.

    For each supported type, an instance is included only when BOTH
    ``WARDEN_<TYPE>_URL`` and ``WARDEN_<TYPE>_API_KEY`` are set (e.g.
    WARDEN_RADARR_URL + WARDEN_RADARR_API_KEY). App-specific prefixes keep the
    shared .env organised. This lets an operator enable whichever instances they
    run purely via .env.
    """
    for arr in ArrType:
        prefix = arr.value.upper()
        url = env.get(f"WARDEN_{prefix}_URL", "").rstrip("/")
        api_key = env.get(f"WARDEN_{prefix}_API_KEY", "")
        if url and api_key:
            yield InstanceConfig(name=arr.value, type=arr, url=url, api_key=api_key)


@dataclass(frozen=True)
class Config:
    instances: tuple[InstanceConfig, ...]
    reserve_pct: float
    fallback_searches_per_day: int
    reset_at_local: str
    include_cutoff_unmet: bool
    poll_interval_sec: float
    db_url: str
    metrics_port: int
    prowlarr_url: str
    prowlarr_api_key: str
    default_query_limit: int
    tz: str
    prowlarr_fallback_on_error: bool
    stale_sweep_enabled: bool
    stale_grace_hours: float
    stale_max_removals_per_tick: int
    stale_mass_fraction: float
    stale_min_queue_for_guard: int
    stale_no_progress_enabled: bool
    stale_no_progress_hours: float
    stale_jitter_tolerance_mb: int
    efficacy_enabled: bool
    efficacy_resolve_minutes: float
    backoff_enabled: bool
    backoff_miss_threshold: int
    backoff_cooldown_days: float
    min_free_bytes: int

    @staticmethod
    def from_env(env: Mapping[str, str] | None = None) -> "Config":
        env = os.environ if env is None else env
        db_path = env.get("WARDEN_DB_PATH", "/state/warden.db")
        return Config(
            instances=tuple(_instances_from_env(env)),
            reserve_pct=float(env.get("WARDEN_RESERVE_PCT", "20")),
            fallback_searches_per_day=int(env.get("WARDEN_FALLBACK_SEARCHES_PER_DAY", "200")),
            reset_at_local=env.get("WARDEN_RESET_AT_LOCAL", "00:00"),
            include_cutoff_unmet=_env_bool(env, "WARDEN_INCLUDE_CUTOFF_UNMET", True),
            poll_interval_sec=float(env.get("WARDEN_POLL_INTERVAL_SEC", "300")),
            db_url=env.get("WARDEN_DB_URL", f"sqlite:///{db_path}"),
            metrics_port=int(env.get("WARDEN_METRICS_PORT", "9090")),
            prowlarr_url=env.get("WARDEN_PROWLARR_URL", "").rstrip("/"),
            prowlarr_api_key=env.get("WARDEN_PROWLARR_API_KEY", ""),
            default_query_limit=int(env.get("WARDEN_DEFAULT_QUERY_LIMIT", "100")),
            tz=env.get("WARDEN_TZ") or env.get("TZ") or "UTC",
            prowlarr_fallback_on_error=_env_bool(env, "WARDEN_PROWLARR_FALLBACK_ON_ERROR", True),
            stale_sweep_enabled=_env_bool(env, "WARDEN_STALE_SWEEP_ENABLED", True),
            stale_grace_hours=float(env.get("WARDEN_STALE_GRACE_HOURS", "48")),
            stale_max_removals_per_tick=int(env.get("WARDEN_STALE_MAX_REMOVALS_PER_TICK", "5")),
            stale_mass_fraction=float(env.get("WARDEN_STALE_MASS_FRACTION", "0.5")),
            stale_min_queue_for_guard=int(env.get("WARDEN_STALE_MIN_QUEUE_FOR_GUARD", "3")),
            stale_no_progress_enabled=_env_bool(env, "WARDEN_STALE_NO_PROGRESS_ENABLED", True),
            stale_no_progress_hours=float(env.get("WARDEN_STALE_NO_PROGRESS_HOURS", "12")),
            stale_jitter_tolerance_mb=int(env.get("WARDEN_STALE_JITTER_TOLERANCE_MB", "0")),
            efficacy_enabled=_env_bool(env, "WARDEN_EFFICACY_ENABLED", True),
            efficacy_resolve_minutes=float(env.get("WARDEN_EFFICACY_RESOLVE_MINUTES", "30")),
            backoff_enabled=_env_bool(env, "WARDEN_BACKOFF_ENABLED", True),
            backoff_miss_threshold=int(env.get("WARDEN_BACKOFF_MISS_THRESHOLD", "3")),
            backoff_cooldown_days=float(env.get("WARDEN_BACKOFF_COOLDOWN_DAYS", "30")),
            min_free_bytes=_min_free_bytes_from_env(env),
        )
