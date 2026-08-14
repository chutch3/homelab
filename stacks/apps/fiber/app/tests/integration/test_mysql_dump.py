from __future__ import annotations

import json
from pathlib import Path

from testcontainers.mysql import MySqlContainer

from fiber.domain.models import DumpFormat, DumpJob, Engine, MovementOutcome
from tests.integration.conftest import make_orchestrator

# Runs against a real MariaDB and drives the host's mariadb-dump / mydumper binaries,
# so the CI test host needs mariadb-client + mydumper installed (mirrors how the
# postgres integration tests assume psql/pg_dump on the host). We connect as root so
# mydumper's default global read lock (RELOAD privilege) is satisfied.

_SEED = (
    "CREATE TABLE a(id INT PRIMARY KEY, name VARCHAR(32));"
    "INSERT INTO a VALUES (1,'x'),(2,'y'),(3,'z');"
    "CREATE TABLE b(id INT PRIMARY KEY);"
    "INSERT INTO b VALUES (10),(20);"
)


def _job(host: str, port: int, fmt: DumpFormat) -> DumpJob:
    return DumpJob(service="t", engine=Engine.MYSQL, host=host, port=port, dbname="test",
                   user="root", secret="pw", schedule="0 3 * * *", options=(), retain=7,
                   fmt=fmt, jobs=2, timeout=300, app=None, schema_version_query=None)


def _seed(maria: MySqlContainer) -> None:
    # Seed via the client inside the mariadb image (no host client needed for setup).
    code, out = maria.exec(["mariadb", "-uroot", "-ppw", "test", "-e", _SEED])
    assert code == 0, out


def _prepare(tmp_path: Path) -> None:
    (tmp_path / "secrets").mkdir()
    (tmp_path / "secrets" / "pw").write_text("pw")


def _reason(rec) -> str:
    # On a CLOGGED movement the dump tool's stderr tail is written to the stool sample.
    if rec.sample_path and Path(rec.sample_path).exists():
        return Path(rec.sample_path).read_text()
    return f"outcome={rec.outcome}"


async def test_mysql_plain_dump_produces_sql_receipt_and_history(tmp_path: Path) -> None:
    _prepare(tmp_path)
    with MySqlContainer("mariadb:11", username="root", password="pw", dbname="test") as maria:
        _seed(maria)
        host, port = maria.get_container_host_ip(), int(maria.get_exposed_port(3306))
        rec = await make_orchestrator(tmp_path).perform(_job(host, port, DumpFormat.PLAIN))

        assert rec.outcome is MovementOutcome.CLEAN, _reason(rec)
        assert rec.bytes_written > 0
        assert rec.receipt_path and Path(rec.receipt_path).exists()
        dumps = list((tmp_path / "bowl" / "t").glob("*.sql"))
        assert len(dumps) == 1
        body = dumps[0].read_text()
        assert "CREATE TABLE" in body and "INSERT INTO" in body


async def test_mysql_directory_dump_via_mydumper(tmp_path: Path) -> None:
    _prepare(tmp_path)
    with MySqlContainer("mariadb:11", username="root", password="pw", dbname="test") as maria:
        _seed(maria)
        host, port = maria.get_container_host_ip(), int(maria.get_exposed_port(3306))
        rec = await make_orchestrator(tmp_path).perform(_job(host, port, DumpFormat.DIRECTORY))

        assert rec.outcome is MovementOutcome.CLEAN, _reason(rec)
        dirs = list((tmp_path / "bowl" / "t").glob("*.dir"))
        assert len(dirs) == 1
        # mydumper writes metadata + per-table schema/data files -> a multi-file directory
        assert len(list(dirs[0].iterdir())) > 1

        # dir-walk size/checksum (built for pg -Fd) must cover the mydumper directory too
        assert rec.bytes_written > 0
        manifest = json.loads(Path(rec.receipt_path).read_text())
        assert manifest["sha256"]
        assert manifest["bytes"] == rec.bytes_written
