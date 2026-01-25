import json
import logging
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "takeout-worker",
        }

        # Add extra fields if present
        if hasattr(record, "job_id"):
            log_data["job_id"] = record.job_id
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "task_type"):
            log_data["task_type"] = record.task_type
        if hasattr(record, "chunk_index"):
            log_data["chunk_index"] = record.chunk_index
        if hasattr(record, "status"):
            log_data["status"] = record.status

        return json.dumps(log_data)
