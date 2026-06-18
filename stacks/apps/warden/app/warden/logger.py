from __future__ import annotations

import logging
import sys
import time

from pythonjsonlogger import jsonlogger


def _configure() -> None:
    root = logging.getLogger("warden")
    if root.handlers:
        return
    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
    )
    formatter.converter = time.gmtime  # UTC timestamps
    handler.setFormatter(formatter)
    root.setLevel(logging.INFO)
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    _configure()
    return logging.getLogger(name)
