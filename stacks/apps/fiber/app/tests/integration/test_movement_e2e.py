import os
import subprocess
from pathlib import Path
import pytest
from prometheus_client import CollectorRegistry
from testcontainers.postgres import PostgresContainer
from fiber.clients.bowl import BowlStorage
from fiber.clock import SystemClock
from fiber.clients.dump_runner import DumpRunner
from fiber.database import Database
from fiber.repositories.history import HistoryRepository
from fiber.metrics import Metrics
from fiber.models import DumpFormat, DumpJob, Engine, MovementOutcome
from fiber.services.orchestrator import MovementOrchestrator
from fiber.clients.secrets import SecretReader
from fiber.clients.swarm import DockerSwarmGateway
from fiber.clients.events import EventBroker

pytestmark = pytest.mark.skipif(os.getenv("FIBER_INTEGRATION") != "1", reason="integration gated")


def _make_orch(tmp_path: Path) -> MovementOrchestrator:
    db = Database(url=f"sqlite:///{tmp_path}/fiber.db")
    return MovementOrchestrator(
        bowl_factory=lambda root: BowlStorage(root=root),
        bowl_root=str(tmp_path / "bowl"),
        secrets=SecretReader(base_dir=str(tmp_path / "secrets")),
        runner=DumpRunner(),
        history=HistoryRepository(session_factory=db.session),
        discovery=DockerSwarmGateway(client_factory=lambda: None),
        clock=SystemClock(),
        fiber_version="0.1.0",
        metrics=Metrics(registry=CollectorRegistry()),
        events=EventBroker(),
    )


async def test_labelled_db_produces_dump_receipt_and_history(tmp_path: Path) -> None:
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "pw").write_text("pw")
    with PostgresContainer("postgres:16-alpine", username="test", password="pw", dbname="test") as pg:
        host, port = pg.get_container_host_ip(), int(pg.get_exposed_port(5432))
        dsn = f"postgresql://test:pw@{host}:{port}/test"
        subprocess.run(["psql", dsn, "-c", "CREATE TABLE t(id int); INSERT INTO t VALUES (1);"], check=True)

        job = DumpJob(service="t", engine=Engine.POSTGRES, host=host, port=port, dbname="test",
                      user="test", secret="pw", schedule="0 3 * * *", options=(), retain=7,
                      fmt=DumpFormat.CUSTOM, jobs=1, timeout=300, app=None, schema_version_query=None)
        orch = _make_orch(tmp_path)

        rec = await orch.perform(job)
        assert rec.outcome is MovementOutcome.CLEAN
        assert rec.receipt_path and Path(rec.receipt_path).exists()
        dumps = list((tmp_path / "bowl" / "t").glob("*.dump"))
        assert len(dumps) == 1


async def test_fiber_path_writes_dump_to_alt_directory(tmp_path: Path) -> None:
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "pw").write_text("pw")
    alt_bowl = tmp_path / "alt"
    with PostgresContainer("postgres:16-alpine", username="test", password="pw", dbname="test") as pg:
        host, port = pg.get_container_host_ip(), int(pg.get_exposed_port(5432))
        dsn = f"postgresql://test:pw@{host}:{port}/test"
        subprocess.run(["psql", dsn, "-c", "CREATE TABLE t(id int); INSERT INTO t VALUES (1);"], check=True)

        job = DumpJob(service="t", engine=Engine.POSTGRES, host=host, port=port, dbname="test",
                      user="test", secret="pw", schedule="0 3 * * *", options=(), retain=7,
                      fmt=DumpFormat.CUSTOM, jobs=1, timeout=300, app=None, schema_version_query=None,
                      path=str(alt_bowl))
        orch = _make_orch(tmp_path)

        rec = await orch.perform(job)
        assert rec.outcome is MovementOutcome.CLEAN
        # dump must be under alt_bowl, not the default bowl_root
        dumps = list((alt_bowl / "t").glob("*.dump"))
        assert len(dumps) == 1
        default_dumps = list((tmp_path / "bowl").glob("**/*.dump"))
        assert len(default_dumps) == 0
