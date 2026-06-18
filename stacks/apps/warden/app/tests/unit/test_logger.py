from __future__ import annotations

import json
import logging
import time

from pythonjsonlogger import jsonlogger

from warden.logger import get_logger


def _format(record_extra: dict) -> dict:
    fmt = jsonlogger.JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
        rename_fields={"asctime": "ts", "levelname": "level", "name": "logger"},
    )
    fmt.converter = time.gmtime
    rec = logging.LogRecord("warden.test", logging.INFO, __file__, 1, "hunt tick", None, None)
    for k, v in record_extra.items():
        setattr(rec, k, v)
    return json.loads(fmt.format(rec))


class TestJsonLogging:
    def test_emits_json_with_renamed_fields_and_extra(self) -> None:
        d = _format({"event": "issued", "source": "radarr", "issued": 3})
        assert d["level"] == "INFO"
        assert d["logger"] == "warden.test"
        assert d["message"] == "hunt tick"
        assert d["event"] == "issued" and d["source"] == "radarr" and d["issued"] == 3

    def test_timestamp_is_utc_iso(self) -> None:
        d = _format({})
        assert d["ts"].endswith("Z")

    def test_get_logger_returns_logger(self) -> None:
        logger = get_logger("warden.x")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "warden.x"
