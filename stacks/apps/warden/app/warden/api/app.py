from __future__ import annotations

from fastapi import FastAPI

from warden.api.routes import health, metrics


def configure_app(app: FastAPI) -> FastAPI:
    app.include_router(health.router)
    app.include_router(metrics.router)
    return app
