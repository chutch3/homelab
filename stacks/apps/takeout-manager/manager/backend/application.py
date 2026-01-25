import os
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing_extensions import Optional

from backend.containers import ManagerContainer
from backend.endpoints import router
from backend.logger import StructuredFormatter

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
logging.basicConfig(level=logging.INFO, handlers=[handler])
logger = logging.getLogger(__name__)


def create_app(container: Optional[ManagerContainer] = None) -> FastAPI:
    if container is None:
        container = ManagerContainer()

    # Use local path for development, Docker path for production
    default_db_path = os.path.join(os.path.dirname(__file__), "..", "db", "takeout.db")
    container.config.db.path.from_env("APP_DB_FILE", default_db_path)

    logger.info("Initializing Takeout Manager", extra={
        "db_path": container.config.db.path()
    })

    app = FastAPI(title="Takeout Manager API")

    # Include API routes
    app.include_router(router)

    # Serve static files (built Vue.js app)
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    assets_dir = os.path.join(static_dir, "assets")

    # Only mount static files if they exist (after frontend is built)
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    if os.path.exists(static_dir) and os.path.isfile(
        os.path.join(static_dir, "index.html")
    ):
        # Catch-all route for SPA - must be last
        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            # If file exists in static dir, serve it
            file_path = os.path.join(static_dir, full_path)
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            # Otherwise serve index.html for SPA routing
            return FileResponse(os.path.join(static_dir, "index.html"))

    return app


# Create app instance for uvicorn
app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
