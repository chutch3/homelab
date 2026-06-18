from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    bowl_path: str
    db_path: str
    db_url: str
    secrets_dir: str
    default_schedule: str
    default_retain: int
    max_concurrent: int
    scan_interval: float
    metrics_port: int
    docker_host: str
    scan_enabled: bool

    @staticmethod
    def from_env() -> "Config":
        db_path = os.getenv("FIBER_DB_PATH", "/state/fiber.db")
        raw_scan_enabled = os.getenv("FIBER_SCAN_ENABLED", "true").strip().lower()
        scan_enabled = raw_scan_enabled not in ("0", "false", "no")
        return Config(
            bowl_path=os.getenv("FIBER_BOWL_PATH", "/backups"),
            db_path=db_path,
            db_url=os.getenv("FIBER_DB_URL", f"sqlite:///{db_path}"),
            secrets_dir=os.getenv("FIBER_SECRETS_DIR", "/run/secrets"),
            default_schedule=os.getenv("FIBER_DEFAULT_SCHEDULE", "0 3 * * *"),
            default_retain=int(os.getenv("FIBER_DEFAULT_RETAIN", "7")),
            max_concurrent=int(os.getenv("FIBER_MAX_CONCURRENT_MOVEMENTS", "2")),
            scan_interval=float(os.getenv("FIBER_SCAN_INTERVAL", "60")),
            metrics_port=int(os.getenv("FIBER_METRICS_PORT", "9090")),
            docker_host=os.getenv("FIBER_DOCKER_HOST", "unix:///var/run/docker.sock"),
            scan_enabled=scan_enabled,
        )
