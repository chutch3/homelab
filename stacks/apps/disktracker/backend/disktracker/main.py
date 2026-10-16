"""The application: configured from the environment into its container, its routes wired to it,
errors answered the same way everywhere, each area's routes included, and the built frontend
served. Run it with `uvicorn disktracker.main:create_app --factory`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from disktracker.catalog import routes as catalog_routes
from disktracker.collection import routes as collection_routes
from disktracker.container import Container
from disktracker.errors import register_error_handlers
from disktracker.openapi import OPENAPI
from disktracker.reporting import routes as reporting_routes


def create_app(container: Container | None = None) -> FastAPI:
    """DISKTRACKER_DATABASE_URL: the database. DISKTRACKER_COLLECTOR_URL: where the collector's
    API is, for testing sources; unset when there is no collector to ask.
    DISKTRACKER_STATIC_DIR: the built frontend to serve beside the API; unset serves the API
    alone, as in development, where the frontend has its own server."""
    if container is None:
        container = Container()

    container.config.database_url.from_env("DISKTRACKER_DATABASE_URL", required=True)
    container.config.collector_url.from_env("DISKTRACKER_COLLECTOR_URL", default=None)
    container.config.static_dir.from_env("DISKTRACKER_STATIC_DIR", default=None)
    container.wire()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        container.database().dispose()

    # Operation ids are the route function names, so generated clients get readable calls.
    app = FastAPI(**OPENAPI, lifespan=lifespan, generate_unique_id_function=lambda r: r.name)
    register_error_handlers(app)
    for area in (catalog_routes, reporting_routes, collection_routes):
        app.include_router(area.router)

    static_dir = container.config.static_dir()
    if static_dir:
        serve_frontend(app, Path(static_dir).resolve())

    return app


def serve_frontend(app: FastAPI, site: Path) -> None:
    """Serve the built frontend in site beside the API."""

    @app.get("/{path:path}", include_in_schema=False)
    def page(path: str) -> FileResponse:
        """A file of the built frontend; any other path that is not a file's is a route inside
        the app, so it gets the app's page."""
        asked = (site / path).resolve()
        if asked.is_file() and asked.is_relative_to(site):
            return FileResponse(asked)
        if path.startswith("api/") or Path(path).suffix:
            raise HTTPException(status_code=404)
        return FileResponse(site / "index.html")
