import json
import logging
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "takeout-manager",
        }

        if hasattr(record, "job_id"):
            log_data["job_id"] = record.job_id
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "chunk_id"):
            log_data["chunk_id"] = record.chunk_id
        if hasattr(record, "status"):
            log_data["status"] = record.status

        return json.dumps(log_data)
