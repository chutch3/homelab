from __future__ import annotations

import os
from collections.abc import Iterator, Mapping

from pydantic import Field, field_validator

from warden.models import ArrType, InstanceConfig
from warden.settings import EnvironmentSettings


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


class Config(EnvironmentSettings):
    instances: tuple[InstanceConfig, ...] = ()
    reserve_pct: float = 20
    fallback_searches_per_day: int = 200
    reset_at_local: str = "00:00"
    include_cutoff_unmet: bool = True
    poll_interval_sec: float = 300
    db_url: str = Field(default="sqlite:////state/warden.db", repr=False)
    metrics_port: int = 9090
    prowlarr_url: str = ""
    prowlarr_api_key: str = Field(default="", repr=False)
    default_query_limit: int = 100
    tz: str = "UTC"
    prowlarr_fallback_on_error: bool = True
    stale_sweep_enabled: bool = True
    stale_grace_hours: float = 48
    stale_max_removals_per_tick: int = 5
    stale_mass_fraction: float = 0.5
    stale_min_queue_for_guard: int = 3
    stale_no_progress_enabled: bool = True
    stale_no_progress_hours: float = 12
    stale_jitter_tolerance_mb: int = 0
    efficacy_enabled: bool = True
    efficacy_resolve_minutes: float = 30
    backoff_enabled: bool = True
    backoff_miss_threshold: int = 3
    backoff_cooldown_days: float = 30
    min_free_gb: float = Field(default=0, allow_inf_nan=False)

    @field_validator("min_free_gb", mode="before")
    @classmethod
    def blank_disables_space_guard(cls, value: object) -> object:
        return 0 if isinstance(value, str) and not value.strip() else value

    @property
    def min_free_bytes(self) -> int:
        return int(self.min_free_gb * 1_000_000_000)

    @field_validator(
        "include_cutoff_unmet", "prowlarr_fallback_on_error", "stale_sweep_enabled",
        "stale_no_progress_enabled", "efficacy_enabled", "backoff_enabled", mode="before",
    )
    @classmethod
    def strip_boolean(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("prowlarr_url")
    @classmethod
    def trim_url(cls, value: str) -> str:
        return value.rstrip("/")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Config:
        env = os.environ if env is None else env
        db_path = env.get("WARDEN_DB_PATH", "/state/warden.db")
        return cls(
            _environment=env,
            instances=tuple(_instances_from_env(env)),
            db_url=env.get("WARDEN_DB_URL", f"sqlite:///{db_path}"),
            tz=env.get("WARDEN_TZ") or env.get("TZ") or "UTC",
        )
