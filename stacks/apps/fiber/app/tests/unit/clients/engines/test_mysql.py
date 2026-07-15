from __future__ import annotations

import pytest

from fiber.clients.engines.base import DumpEngine
from fiber.clients.engines.mysql import MysqlEngine, mysql_defaults_body
from fiber.domain.models import DumpFormat, DumpJob
from tests.factories import MysqlDumpJobFactory


def _job(fmt: DumpFormat, jobs: int = 1, options: tuple[str, ...] = (), **kw: object) -> DumpJob:
    return MysqlDumpJobFactory.build(fmt=fmt, jobs=jobs, options=options, **kw)


class TestMysqlEngine:
    @pytest.fixture()
    def subject(self) -> MysqlEngine:
        return MysqlEngine()

    def test_satisfies_dump_engine_protocol(self, subject: MysqlEngine) -> None:
        assert isinstance(subject, DumpEngine)

    def test_plain_uses_mariadb_dump_with_result_file_and_creds(self, subject: MysqlEngine) -> None:
        argv = subject.build_argv(_job(DumpFormat.PLAIN), "/bowl/x.sql", "/tmp/c.cnf")
        assert argv == ["mariadb-dump", "--defaults-extra-file=/tmp/c.cnf",
                        "-h", "postal-db", "-P", "3306", "-u", "postal",
                        "--result-file", "/bowl/x.sql", "postal"]

    def test_plain_options_precede_db_positional(self, subject: MysqlEngine) -> None:
        # bare words after <db> are read as a table list, so options + --result-file
        # must come before the database name.
        argv = subject.build_argv(
            _job(DumpFormat.PLAIN, dbname="postaldb", options=("--single-transaction",)),
            "/bowl/x.sql", "/tmp/c.cnf")
        assert argv[-1] == "postaldb"
        assert "--single-transaction" in argv[:-1]
        assert "--result-file" in argv[:-1]

    def test_directory_uses_mydumper_with_threads(self, subject: MysqlEngine) -> None:
        argv = subject.build_argv(_job(DumpFormat.DIRECTORY, jobs=4), "/bowl/x.dir", "/tmp/c.cnf")
        assert argv[0] == "mydumper"
        assert "--defaults-extra-file=/tmp/c.cnf" in argv
        assert "--protocol=tcp" in argv  # Fiber dumps over the network, never a local socket
        assert "-B" in argv and argv[argv.index("-B") + 1] == "postal"
        assert "-o" in argv and argv[argv.index("-o") + 1] == "/bowl/x.dir"
        assert "-t" in argv and argv[argv.index("-t") + 1] == "4"

    def test_binaries_are_overridable(self) -> None:
        engine = MysqlEngine(dump_binary="/x/mariadb-dump", mydumper_binary="/x/mydumper")
        assert engine.build_argv(_job(DumpFormat.PLAIN), "/bowl/x.sql", "/tmp/c.cnf")[0] == "/x/mariadb-dump"
        assert engine.build_argv(_job(DumpFormat.DIRECTORY), "/bowl/x.dir", "/tmp/c.cnf")[0] == "/x/mydumper"

    def test_dump_env_is_empty(self, subject: MysqlEngine) -> None:
        assert subject.dump_env("pw") == {}

    def test_credentials_content_carries_password_for_both_tools(self, subject: MysqlEngine) -> None:
        # mariadb-dump reads [client]; mydumper reads its own [mydumper] group
        assert subject.credentials_content("s3cr3t") == (
            "[client]\npassword=s3cr3t\n[mydumper]\npassword=s3cr3t\n")

    def test_probe_argv_is_mariadb_admin_ping(self, subject: MysqlEngine) -> None:
        job = MysqlDumpJobFactory.build(host="postal-db", port=3306, user="postal")
        assert subject.probe_argv(job) == [
            "mariadb-admin", "ping", "-h", "postal-db", "-P", "3306", "-u", "postal"]


def test_mysql_defaults_body_has_both_sections() -> None:
    assert mysql_defaults_body("pw") == "[client]\npassword=pw\n[mydumper]\npassword=pw\n"
