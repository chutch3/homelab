from __future__ import annotations

import os
import subprocess

import pytest
from testcontainers.postgres import PostgresContainer

from fiber.clients.dump_runner import DumpRunner
from fiber.models import DumpFormat, DumpJob, Engine

pytestmark = pytest.mark.skipif(os.getenv("FIBER_INTEGRATION") != "1", reason="integration gated")


def _job(host: str, port: int, fmt: DumpFormat) -> DumpJob:
    return DumpJob(service="t", engine=Engine.POSTGRES, host=host, port=port, dbname="test",
                   user="test", secret="s", schedule="0 3 * * *", options=(), retain=7,
                   fmt=fmt, jobs=1, timeout=300, app=None, schema_version_query=None)


class TestDumpRunner:
    async def test_dump_then_restore_roundtrip(self, tmp_path: pytest.TempPathFactory) -> None:
        with PostgresContainer("postgres:16-alpine", username="test", password="pw", dbname="test") as pg:
            host = pg.get_container_host_ip()
            port = int(pg.get_exposed_port(5432))
            dsn = f"postgresql://test:pw@{host}:{port}/test"
            subprocess.run(["psql", dsn, "-c", "CREATE TABLE t(id int); INSERT INTO t VALUES (1),(2),(3);"], check=True)

            out = str(tmp_path / "dump.custom")
            outcome = await DumpRunner().run(_job(host, port, DumpFormat.CUSTOM), password="pw", out_path=out)
            assert outcome.returncode == 0 and not outcome.cancelled

            subprocess.run(["psql", dsn, "-c", "DROP TABLE t;"], check=True)
            subprocess.run(["pg_restore", "-d", dsn, out], check=True)
            result = subprocess.run(["psql", dsn, "-tAc", "SELECT count(*) FROM t;"],
                                    check=True, capture_output=True, text=True)
            assert result.stdout.strip() == "3"
