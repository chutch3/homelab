from __future__ import annotations

import asyncio
import signal

import uvicorn
from fastapi import FastAPI

import warden.routes as routes
from warden import __version__
from warden.container import Container
from warden.logger import get_logger
from warden.loop import _hunt_loop
from warden.routes import health

_logger = get_logger("warden.main")


def create_app(container: Container) -> FastAPI:
    container.wire(modules=["warden.loop", "warden.routes.health"])
    app = FastAPI(title="Warden")
    app.include_router(routes.router)
    app.include_router(health.router)
    return app


async def _amain() -> None:
    container = Container()
    cfg = container.config()
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
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    app = create_app(container)
    server = uvicorn.Server(uvicorn.Config(app, host="0.0.0.0", port=cfg.metrics_port, log_level="info"))
    await asyncio.gather(server.serve(), _hunt_loop(stop))


def main() -> None:
    asyncio.run(_amain())


if __name__ == "__main__":
    main()
