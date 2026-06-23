"""Unit tests for the StructuredFormatter JSON log formatter."""

import json
import logging

from worker.logger import StructuredFormatter


def _record(**extra):
    record = logging.LogRecord(
        name="worker.test", level=logging.INFO, pathname=__file__, lineno=1,
        msg="hello %s", args=("world",), exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestStructuredFormatter:
    def test_format_emits_core_fields_as_json(self):
        out = json.loads(StructuredFormatter().format(_record()))
        assert out["level"] == "INFO"
        assert out["logger"] == "worker.test"
        assert out["message"] == "hello world"  # args interpolated
        assert out["service"] == "takeout-worker"
        assert out["timestamp"].endswith("Z")

    def test_format_includes_optional_context_fields_when_present(self):
        out = json.loads(StructuredFormatter().format(
            _record(job_id="j1", task_id="t1", task_type="download", chunk_index=3, status="ok")
        ))
        assert out["job_id"] == "j1"
        assert out["task_id"] == "t1"
        assert out["task_type"] == "download"
        assert out["chunk_index"] == 3
        assert out["status"] == "ok"

    def test_format_omits_optional_fields_when_absent(self):
        out = json.loads(StructuredFormatter().format(_record()))
        for key in ("job_id", "task_id", "task_type", "chunk_index", "status"):
            assert key not in out
