import os
import logging
import uvicorn

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional

from backend.containers import ManagerContainer
from backend.endpoints import router
from backend.logger import StructuredFormatter


def create_app(container: Optional[ManagerContainer] = None) -> FastAPI:
    if container is None:
        container = ManagerContainer()
        handler = logging.StreamHandler()
        handler.setFormatter(StructuredFormatter())
        logging.basicConfig(level=logging.INFO, handlers=[handler])

    logger = logging.getLogger(__name__)

    default_db_path = os.path.join(os.path.dirname(__file__), "..", "db", "takeout.db")
    container.config.db.path.from_env("APP_DB_FILE", default_db_path)

    db = container.database()
    db.ensure_path_exists()
    db.create_tables()

    logger.info("Initializing Takeout Manager", extra={
        "db_path": container.config.db.path()
    })

    app = FastAPI(title="Takeout Manager API")

    app.include_router(router)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    assets_dir = os.path.join(static_dir, "assets")

    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if os.path.exists(static_dir) and os.path.isfile(
        os.path.join(static_dir, "index.html")
    ):
        # Catch-all route for SPA - must be last
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(static_dir, "index.html"))

    return app


if __name__ == "__main__":
    uvicorn.run("backend.application:create_app", factory=True, host="0.0.0.0", port=8000)
