from __future__ import annotations

import asyncio
import signal
from collections.abc import Awaitable, Callable

import uvicorn

from warden import __version__
from warden.config import Config
from warden.logger import get_logger

_logger = get_logger("warden.serve")


async def serve(
    cfg: Config, server: uvicorn.Server, stop: asyncio.Event,
    hunt: Callable[[], Awaitable[None]], profiles: Callable[[], Awaitable[None]],
) -> None:
    _logger.info("warden starting", extra={
        "event": "startup",
        "version": __version__,
        "sources": [i.name for i in cfg.instances],
        "prowlarr": bool(cfg.prowlarr_url),
        "prowlarr_url": cfg.prowlarr_url or None,
        "tz": cfg.tz,
        "reserve_pct": cfg.reserve_pct,
        "fallback_per_day": cfg.fallback_searches_per_day,
        "default_query_limit": cfg.default_query_limit,
        "poll_interval_sec": cfg.poll_interval_sec,
        "prowlarr_fallback_on_error": cfg.prowlarr_fallback_on_error,
    })
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    await asyncio.gather(server.serve(), hunt(), profiles())
