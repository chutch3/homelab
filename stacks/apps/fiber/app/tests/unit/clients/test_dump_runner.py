from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from fiber.models import DumpFormat, DumpJob, Engine
from fiber.clients.dump_runner import (
    DumpRunner,
    RunOutcome,
    build_pg_dump_argv,
    select_pg_dump_binary,
)
from tests.factories import DumpJobFactory


# ---------------------------------------------------------------------------
# Pure-function tests — stay flat (no class)
# ---------------------------------------------------------------------------

def _job(fmt: DumpFormat, jobs: int = 1, options: tuple[str, ...] = ()) -> DumpJob:
    return DumpJobFactory.build(fmt=fmt, jobs=jobs, options=options)


def test_custom_format_argv() -> None:
    argv = build_pg_dump_argv(_job(DumpFormat.CUSTOM, options=("--clean",)), out_path="/bowl/x.dump")
    assert argv == ["pg_dump", "-h", "kenku-pg", "-p", "5432", "-U", "kenku", "-d", "kenku",
                    "-F", "c", "--clean", "-f", "/bowl/x.dump"]


def test_directory_format_adds_jobs() -> None:
    argv = build_pg_dump_argv(_job(DumpFormat.DIRECTORY, jobs=4), out_path="/bowl/x.dir")
    assert "-F" in argv and argv[argv.index("-F") + 1] == "d"
    assert "-j" in argv and argv[argv.index("-j") + 1] == "4"


def test_build_pg_dump_argv_uses_binary_param() -> None:
    argv = build_pg_dump_argv(_job(DumpFormat.CUSTOM), out_path="/bowl/x.dump", binary="/x/pg_dump")
    assert argv[0] == "/x/pg_dump"


def test_select_pg_dump_binary_picks_highest_major(tmp_path: Path) -> None:
    for major in (13, 16, 14):
        (tmp_path / str(major) / "bin").mkdir(parents=True)
    result = select_pg_dump_binary(bindir=str(tmp_path))
    assert result == f"{tmp_path}/16/bin/pg_dump"


def test_select_pg_dump_binary_falls_back_when_no_dirs(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = select_pg_dump_binary(bindir=str(empty))
    assert result == "pg_dump"


def test_select_pg_dump_binary_ignores_non_integer_dirs(tmp_path: Path) -> None:
    (tmp_path / "16" / "bin").mkdir(parents=True)
    (tmp_path / "utils").mkdir()
    result = select_pg_dump_binary(bindir=str(tmp_path))
    assert result == f"{tmp_path}/16/bin/pg_dump"


# ---------------------------------------------------------------------------
# FakeProcess + factory fixture
# ---------------------------------------------------------------------------

class FakeProcess:
    def __init__(self, returncode: int = 0, stderr_data: bytes = b"", *, hang: bool = False) -> None:
        self._returncode: int | None = None
        self._final_returncode = returncode
        self._stderr_data = stderr_data
        self._hang = hang
        self.stderr: Any = self
        self.terminated = False
        self.killed = False

    async def read(self) -> bytes:
        return self._stderr_data

    async def wait(self) -> int:
        if self._hang:
            await asyncio.sleep(9999)
        self._returncode = self._final_returncode
        return self._returncode

    @property
    def returncode(self) -> int | None:
        return self._returncode

    def terminate(self) -> None:
        self.terminated = True
        self._hang = False
        self._returncode = -1

    def kill(self) -> None:
        self.killed = True
        self._returncode = -1


def _make_job(timeout: float | None = None) -> DumpJob:
    return DumpJobFactory.build(timeout=timeout)


# ---------------------------------------------------------------------------
# Class tests for DumpRunner.run()
# ---------------------------------------------------------------------------

class TestDumpRunner:
    @pytest.fixture()
    def fake_proc(self) -> FakeProcess:
        return FakeProcess(returncode=0, stderr_data=b"")

    @pytest.fixture()
    def subject(self, fake_proc: FakeProcess) -> DumpRunner:
        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return fake_proc
        return DumpRunner(pg_dump_binary="pg_dump", process_factory=factory)

    async def test_success_returns_zero_returncode(
        self, subject: DumpRunner, fake_proc: FakeProcess
    ) -> None:
        outcome = await subject.run(_make_job(), password="pw", out_path="/bowl/x.dump")
        assert outcome == RunOutcome(returncode=0, stderr_tail="", cancelled=False)

    async def test_failure_captures_stderr_tail(self, fake_proc: FakeProcess) -> None:
        fake_proc._final_returncode = 1
        fake_proc._stderr_data = b"boom"

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return fake_proc

        runner = DumpRunner(pg_dump_binary="pg_dump", process_factory=factory)
        outcome = await runner.run(_make_job(), password="pw", out_path="/bowl/x.dump")
        assert outcome.returncode == 1
        assert outcome.cancelled is False
        assert "boom" in outcome.stderr_tail

    async def test_timeout_cancels_and_terminates(self) -> None:
        proc = FakeProcess(returncode=0, hang=True)

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return proc

        runner = DumpRunner(pg_dump_binary="pg_dump", process_factory=factory)
        outcome = await runner.run(_make_job(timeout=0.01), password="pw", out_path="/bowl/x.dump")
        assert outcome.cancelled is True
        assert proc.terminated is True

    async def test_external_cancel_cancels_and_terminates(self) -> None:
        proc = FakeProcess(returncode=0, hang=True)

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return proc

        runner = DumpRunner(pg_dump_binary="pg_dump", process_factory=factory)

        async def _run() -> RunOutcome:
            return await runner.run(_make_job(), password="pw", out_path="/bowl/x.dump")

        task = asyncio.create_task(_run())
        await asyncio.sleep(0.01)
        task.cancel()
        outcome = await task
        assert outcome.cancelled is True
        assert proc.terminated is True
