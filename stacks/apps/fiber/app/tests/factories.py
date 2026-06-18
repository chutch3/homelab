from __future__ import annotations

from datetime import datetime, timezone

from polyfactory.factories.dataclass_factory import DataclassFactory

from fiber.models import DumpFormat, DumpJob, Engine, MovementOutcome, MovementRecord


class DumpJobFactory(DataclassFactory[DumpJob]):
    __model__ = DumpJob

    service = "kenku-pg"
    engine = Engine.POSTGRES
    host = "kenku-pg"
    port = 5432
    dbname = "kenku"
    user = "kenku"
    secret = "kenku_db_password"
    schedule = "0 3 * * *"
    options = ()
    retain = 7
    fmt = DumpFormat.CUSTOM
    jobs = 1
    timeout = None
    app = None
    schema_version_query = None


class MovementRecordFactory(DataclassFactory[MovementRecord]):
    __model__ = MovementRecord

    service = "kenku-pg"
    engine = Engine.POSTGRES
    started_at = datetime(2026, 6, 15, 3, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 6, 15, 3, 0, tzinfo=timezone.utc)
    outcome = MovementOutcome.CLEAN
    bytes_written = 100
    bristol_type = 4
    sample_path = None
    receipt_path = None
    app_image = None
    app_digest = None
