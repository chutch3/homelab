"""Structured logging configuration for the takeout-manager."""
import json
import logging
import sys
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": "takeout-manager",
        }

        # Add extra fields if present
        if hasattr(record, "job_id"):
            log_data["job_id"] = record.job_id
        if hasattr(record, "task_id"):
            log_data["task_id"] = record.task_id
        if hasattr(record, "chunk_id"):
            log_data["chunk_id"] = record.chunk_id
        if hasattr(record, "status"):
            log_data["status"] = record.status

        return json.dumps(log_data)


def configure_logging(level: str = "INFO"):
    """Configure structured logging for the manager.

    Args:
        level: Logging level (default: INFO)

    Yields:
        None - this is a generator for resource management
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    yield

    # Cleanup on shutdown
    root_logger.removeHandler(handler)
    handler.close()
