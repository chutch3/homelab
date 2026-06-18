from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncGenerator

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

import fiber.routes as routes
from fiber.config import Config
from fiber.container import Container
from fiber.logger import get_logger
from fiber.loop import _scan_loop
from fiber.routes import dashboard

_logger = get_logger("fiber.main")


def create_app(container: Container | None = None) -> FastAPI:
    container = container or Container()
    container.wire(modules=[
        "fiber.loop",
        "fiber.routes.health",
        "fiber.routes.dashboard",
    ])

    @contextlib.asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        task: asyncio.Task[None] | None = None
        if container.config().scan_enabled:
            stop = asyncio.Event()
            task = asyncio.create_task(_scan_loop(stop))
            try:
                yield
            finally:
                stop.set()
                pool = container.pool()
                for svc in list(pool.running_services()):
                    pool.cancel(svc)
                if task is not None:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
        else:
            yield

    app = FastAPI(title="Fiber", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory="fiber/static"), name="static")
    app.include_router(routes.router)
    app.include_router(dashboard.router)
    return app


def main() -> None:
    cfg = Config.from_env()
    uvicorn.run(create_app(), host="0.0.0.0", port=cfg.metrics_port, log_level="info")


if __name__ == "__main__":
    main()
