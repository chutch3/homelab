from __future__ import annotations

import os
from collections.abc import Iterator
from dataclasses import dataclass

from warden.models import ArrType, InstanceConfig


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _instances_from_env() -> Iterator[InstanceConfig]:
    """Discover configured *arr instances from env vars.

    For each supported type, an instance is included only when BOTH
    ``WARDEN_<TYPE>_URL`` and ``WARDEN_<TYPE>_API_KEY`` are set (e.g.
    WARDEN_RADARR_URL + WARDEN_RADARR_API_KEY). App-specific prefixes keep the
    shared .env organised. This lets an operator enable whichever instances they
    run purely via .env.
    """
    for arr in ArrType:
        prefix = arr.value.upper()
        url = os.getenv(f"WARDEN_{prefix}_URL", "").rstrip("/")
        api_key = os.getenv(f"WARDEN_{prefix}_API_KEY", "")
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

    @staticmethod
    def from_env() -> "Config":
        db_path = os.getenv("WARDEN_DB_PATH", "/state/warden.db")
        return Config(
            instances=tuple(_instances_from_env()),
            reserve_pct=float(os.getenv("WARDEN_RESERVE_PCT", "20")),
            fallback_searches_per_day=int(os.getenv("WARDEN_FALLBACK_SEARCHES_PER_DAY", "200")),
            reset_at_local=os.getenv("WARDEN_RESET_AT_LOCAL", "00:00"),
            include_cutoff_unmet=_env_bool("WARDEN_INCLUDE_CUTOFF_UNMET", True),
            poll_interval_sec=float(os.getenv("WARDEN_POLL_INTERVAL_SEC", "300")),
            db_url=os.getenv("WARDEN_DB_URL", f"sqlite:///{db_path}"),
            metrics_port=int(os.getenv("WARDEN_METRICS_PORT", "9090")),
            prowlarr_url=os.getenv("WARDEN_PROWLARR_URL", "").rstrip("/"),
            prowlarr_api_key=os.getenv("WARDEN_PROWLARR_API_KEY", ""),
            default_query_limit=int(os.getenv("WARDEN_DEFAULT_QUERY_LIMIT", "100")),
            tz=os.getenv("WARDEN_TZ") or os.getenv("TZ") or "UTC",
            prowlarr_fallback_on_error=_env_bool("WARDEN_PROWLARR_FALLBACK_ON_ERROR", True),
            stale_sweep_enabled=_env_bool("WARDEN_STALE_SWEEP_ENABLED", True),
            stale_grace_hours=float(os.getenv("WARDEN_STALE_GRACE_HOURS", "48")),
            stale_max_removals_per_tick=int(os.getenv("WARDEN_STALE_MAX_REMOVALS_PER_TICK", "5")),
            stale_mass_fraction=float(os.getenv("WARDEN_STALE_MASS_FRACTION", "0.5")),
            stale_min_queue_for_guard=int(os.getenv("WARDEN_STALE_MIN_QUEUE_FOR_GUARD", "3")),
            stale_no_progress_enabled=_env_bool("WARDEN_STALE_NO_PROGRESS_ENABLED", True),
            stale_no_progress_hours=float(os.getenv("WARDEN_STALE_NO_PROGRESS_HOURS", "12")),
            stale_jitter_tolerance_mb=int(os.getenv("WARDEN_STALE_JITTER_TOLERANCE_MB", "0")),
            efficacy_enabled=_env_bool("WARDEN_EFFICACY_ENABLED", True),
            efficacy_resolve_minutes=float(os.getenv("WARDEN_EFFICACY_RESOLVE_MINUTES", "30")),
            backoff_enabled=_env_bool("WARDEN_BACKOFF_ENABLED", True),
            backoff_miss_threshold=int(os.getenv("WARDEN_BACKOFF_MISS_THRESHOLD", "3")),
            backoff_cooldown_days=float(os.getenv("WARDEN_BACKOFF_COOLDOWN_DAYS", "30")),
        )
