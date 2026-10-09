"""Logging for the whole process: one JSON object per line on stdout, saying when (ts, UTC),
how severe (level), which module (logger) and what happened (event), plus the event's fields."""

import logging
import sys
import time

from pythonjsonlogger.json import JsonFormatter

# Third-party loggers that log every request at INFO: only worth seeing when debugging.
CHATTY = ("httpx", "httpcore")


def configure(level: str) -> None:
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        rename_fields={
            "asctime": "ts",
            "levelname": "level",
            "name": "logger",
            "message": "event",
        },
    )
    formatter.converter = time.gmtime
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in CHATTY:
        logging.getLogger(name).setLevel(logging.DEBUG if level == "DEBUG" else logging.WARNING)
