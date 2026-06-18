from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Engine(str, Enum):
    POSTGRES = "postgres"
    MYSQL = "mysql"


class DumpFormat(str, Enum):
    CUSTOM = "custom"
    DIRECTORY = "directory"
    PLAIN = "plain"


class MovementOutcome(str, Enum):
    CLEAN = "clean"
    CLOGGED = "clogged"
    PINCHED = "pinched"


@dataclass(frozen=True)
class DumpJob:
    service: str
    engine: Engine
    host: str
    port: int
    dbname: str
    user: str
    secret: str
    schedule: str
    options: tuple[str, ...]
    retain: int
    fmt: DumpFormat
    jobs: int
    timeout: float | None
    app: str | None
    schema_version_query: str | None
    path: str | None = None

    @property
    def bowl_key(self) -> str:
        return self.service


@dataclass(frozen=True)
class MisconfiguredJob:
    service: str
    errors: tuple[str, ...]


@dataclass(frozen=True)
class BowlEntry:
    path: str
    size_bytes: int
    modified_at: datetime
    is_temp: bool


@dataclass(frozen=True)
class MovementRecord:
    service: str
    engine: Engine
    started_at: datetime
    finished_at: datetime
    outcome: MovementOutcome
    bytes_written: int
    bristol_type: int | None
    sample_path: str | None
    receipt_path: str | None
    app_image: str | None
    app_digest: str | None


@dataclass(frozen=True)
class Manifest:
    service: str
    engine: Engine
    server_version: str
    app_service: str | None
    app_image: str | None
    app_digest: str | None
    fmt: DumpFormat
    jobs: int
    bytes: int
    sha256: str
    fiber_version: str
    schema_marker: str | None
    finished_at: str
