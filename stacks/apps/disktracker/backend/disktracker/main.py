"""Process entry point: load configuration and assemble the application."""

import os

from disktracker.web import create_app

app = create_app(
    os.environ["DISKTRACKER_DATABASE_URL"],
    os.environ.get("DISKTRACKER_COLLECTOR_URL"),
    os.environ.get("DISKTRACKER_STATIC_DIR"),
)
