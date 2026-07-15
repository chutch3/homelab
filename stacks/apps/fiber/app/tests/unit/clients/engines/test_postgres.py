from __future__ import annotations

from pathlib import Path

import pytest

from fiber.clients.engines.base import DumpEngine
from fiber.clients.engines.postgres import PostgresEngine, select_pg_dump_binary
from fiber.domain.models import DumpFormat, DumpJob
from tests.factories import DumpJobFactory


def _job(fmt: DumpFormat, jobs: int = 1, options: tuple[str, ...] = ()) -> DumpJob:
    return DumpJobFactory.build(fmt=fmt, jobs=jobs, options=options)


class TestPostgresEngine:
    @pytest.fixture()
    def subject(self) -> PostgresEngine:
        return PostgresEngine(binary="pg_dump")

    def test_satisfies_dump_engine_protocol(self, subject: PostgresEngine) -> None:
        assert isinstance(subject, DumpEngine)

    def test_custom_format_argv(self, subject: PostgresEngine) -> None:
        argv = subject.build_argv(_job(DumpFormat.CUSTOM, options=("--clean",)), "/bowl/x.dump")
        assert argv == ["pg_dump", "-h", "kenku-pg", "-p", "5432", "-U", "kenku", "-d", "kenku",
                        "-F", "c", "--clean", "-f", "/bowl/x.dump"]

    def test_directory_format_adds_jobs(self, subject: PostgresEngine) -> None:
        argv = subject.build_argv(_job(DumpFormat.DIRECTORY, jobs=4), "/bowl/x.dir")
        assert "-F" in argv and argv[argv.index("-F") + 1] == "d"
        assert "-j" in argv and argv[argv.index("-j") + 1] == "4"

    def test_binary_is_used(self) -> None:
        engine = PostgresEngine(binary="/x/pg_dump")
        assert engine.build_argv(_job(DumpFormat.CUSTOM), "/bowl/x.dump")[0] == "/x/pg_dump"

    def test_dump_env_sets_pgpassword(self, subject: PostgresEngine) -> None:
        assert subject.dump_env("pw") == {"PGPASSWORD": "pw"}

    def test_credentials_content_is_none(self, subject: PostgresEngine) -> None:
        assert subject.credentials_content("pw") is None

    def test_probe_argv_is_pg_isready(self, subject: PostgresEngine) -> None:
        job = DumpJobFactory.build(host="kenku-pg", port=5432, user="kenku")
        assert subject.probe_argv(job) == [
            "pg_isready", "-h", "kenku-pg", "-p", "5432", "-U", "kenku"]


class TestSelectPgDumpBinary:
    def test_picks_highest_major(self, tmp_path: Path) -> None:
        for major in (13, 16, 14):
            (tmp_path / str(major) / "bin").mkdir(parents=True)
        assert select_pg_dump_binary(bindir=str(tmp_path)) == f"{tmp_path}/16/bin/pg_dump"

    def test_falls_back_when_no_dirs(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        assert select_pg_dump_binary(bindir=str(empty)) == "pg_dump"

    def test_ignores_non_integer_dirs(self, tmp_path: Path) -> None:
        (tmp_path / "16" / "bin").mkdir(parents=True)
        (tmp_path / "utils").mkdir()
        assert select_pg_dump_binary(bindir=str(tmp_path)) == f"{tmp_path}/16/bin/pg_dump"
