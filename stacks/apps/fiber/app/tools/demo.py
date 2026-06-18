"""Demo — runs the REAL Fiber app (real Container: SQLite history,
BowlStorage, WorkerPool, EventBroker, DashboardService, create_app wiring).
The scan loop is disabled (FIBER_SCAN_ENABLED=false) so the demo works without
a Docker cluster; RegistryState is seeded directly and history rows are written
to real SQLite so the wall shows a spread of derived statuses.
View at http://localhost:8099/"""
from __future__ import annotations

import os

os.environ.setdefault("FIBER_SCAN_ENABLED", "false")
os.environ.setdefault("FIBER_DB_PATH", "/tmp/fiber-local/fiber.db")
os.environ.setdefault("FIBER_BOWL_PATH", "/tmp/fiber-local/bowl")
os.environ.setdefault("FIBER_SECRETS_DIR", "/tmp/fiber-local/secrets")
os.makedirs("/tmp/fiber-local/bowl", exist_ok=True)
os.makedirs("/tmp/fiber-local/secrets", exist_ok=True)

from datetime import datetime, timedelta, timezone

import uvicorn

from fiber.container import Container
from fiber.main import create_app
from fiber.models import DumpFormat, DumpJob, Engine, MisconfiguredJob, MovementOutcome, MovementRecord
from fiber.services.registry_state import RegistryState, Snapshot

UTC = timezone.utc
NOW = datetime.now(UTC)


def _job(s: str, path: str | None = None) -> DumpJob:
    return DumpJob(service=s, engine=Engine.POSTGRES, host=s, port=5432, dbname=s, user=s,
                   secret=f"{s}_pw", schedule="0 3 * * *", options=(), retain=7,
                   fmt=DumpFormat.CUSTOM, jobs=1, timeout=None, app=f"app-{s}",
                   schema_version_query=None, path=path)


JOBS = [_job("authentik"), _job("excalidraw"), _job("prefect"),
        _job("librechat"), _job("kenku"), _job("immich", path="/mnt/big/immich")]
MISCONFIGURED = [MisconfiguredJob(service="paperless", errors=("missing fiber.secret",))]
SKIPPED = [("traefik", "no fiber.enable label"), ("vaultwarden-db", "not on the backups network")]


def _rec(s: str, mins_ago: int, outcome: MovementOutcome, sample_path: str | None = None) -> MovementRecord:
    t = NOW - timedelta(minutes=mins_ago)
    return MovementRecord(service=s, engine=Engine.POSTGRES, started_at=t, finished_at=t,
                          outcome=outcome, bytes_written=1_200_000_000 if s == "kenku" else 240_000_000,
                          bristol_type=4, sample_path=sample_path, receipt_path=None,
                          app_image=f"{s}:1.4", app_digest="sha256:demo")


def main() -> None:
    c = Container()
    rs = RegistryState()
    rs.set(Snapshot(jobs=JOBS, misconfigured=MISCONFIGURED, skipped=SKIPPED))
    c.registry_state.override(rs)

    # seed REAL sqlite history so derive_status produces a spread (scan loop disabled => no dumps fire)
    hist = c.history_repository()
    for s in ("authentik", "kenku", "immich"):
        hist.record(_rec(s, 5, MovementOutcome.CLEAN))
    sample = "/tmp/fiber-local/bowl/excalidraw.stool.log"
    with open(sample, "w") as f:
        f.write("pg_dump: error: connection failed\nFATAL: password authentication failed\n-> secret 'excalidraw_pw' not readable by Fiber")
    hist.record(_rec("excalidraw", 60, MovementOutcome.CLEAN))
    hist.record(_rec("excalidraw", 1, MovementOutcome.CLOGGED, sample_path=sample))
    hist.record(_rec("prefect", 30, MovementOutcome.CLEAN))
    hist.record(_rec("prefect", 1, MovementOutcome.PINCHED))
    # librechat: no history -> Constipated

    print(">>> demo: REAL Fiber (all components wired, scan loop disabled) at http://localhost:8099/")
    uvicorn.run(create_app(c), host="0.0.0.0", port=8099, log_level="warning")


if __name__ == "__main__":
    main()
