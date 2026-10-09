"""Settings from the environment (12-factor)."""

from collections.abc import Mapping
from dataclasses import dataclass

LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR")


@dataclass(frozen=True)
class Config:
    """Which stores to read, and how, is configured on disktracker's Admin page, not here."""

    disktracker_url: str
    min_delay_seconds: float
    run_once: bool
    poll_seconds: float
    retry_delay_seconds: float
    log_level: str
    # FlareSolverr, for sources fetched through a browser; none means they cannot run.
    flaresolverr_url: str | None = None
    # An HTTP proxy (a VPN's, say) every store is fetched through, so stores see its address
    # and not the collector's; none fetches them directly. disktracker is never asked through it.
    proxy_url: str | None = None
    # The port the collector's API (source previews) listens on; none means no API.
    api_port: int | None = None
    # The longest a source preview reads a store before giving up and saying how far it got.
    preview_seconds: float = 120.0

    @classmethod
    def from_env(cls, environ: Mapping[str, str]) -> "Config":
        log_level = environ.get("LOG_LEVEL", "INFO").strip().upper()
        if log_level not in LOG_LEVELS:
            raise ValueError(f"Unknown LOG_LEVEL: {log_level}")
        return cls(
            disktracker_url=environ["DISKTRACKER_URL"].rstrip("/"),
            min_delay_seconds=float(environ.get("COLLECTOR_MIN_DELAY_SECONDS", "2")),
            run_once=environ.get("COLLECTOR_RUN_ONCE", "") == "1",
            poll_seconds=float(environ.get("COLLECTOR_POLL_SECONDS", "60")),
            retry_delay_seconds=float(environ.get("COLLECTOR_RETRY_DELAY_SECONDS", "0.5")),
            log_level=log_level,
            flaresolverr_url=environ.get("FLARESOLVERR_URL", "").strip().rstrip("/") or None,
            proxy_url=environ.get("COLLECTOR_PROXY_URL", "").strip().rstrip("/") or None,
            api_port=int(environ["COLLECTOR_API_PORT"])
            if environ.get("COLLECTOR_API_PORT")
            else None,
            preview_seconds=float(environ.get("COLLECTOR_PREVIEW_SECONDS", "120")),
        )
