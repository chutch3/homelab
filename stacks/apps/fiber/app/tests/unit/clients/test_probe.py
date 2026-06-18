from __future__ import annotations

import asyncio
from typing import Any

import pytest

from fiber.clients.probe import ConnectivityProbe, ProbeResult, build_pg_isready_argv
from tests.factories import DumpJobFactory


# ---------------------------------------------------------------------------
# Pure-function tests
# ---------------------------------------------------------------------------


def test_build_pg_isready_argv_basic() -> None:
    job = DumpJobFactory.build(service="kenku-pg", host="kenku-pg", port=5432, user="kenku")
    argv = build_pg_isready_argv(job)
    assert argv == ["pg_isready", "-h", "kenku-pg", "-p", "5432", "-U", "kenku"]


def test_build_pg_isready_argv_custom_port() -> None:
    job = DumpJobFactory.build(host="mydb", port=5433, user="admin")
    argv = build_pg_isready_argv(job)
    assert argv[0] == "pg_isready"
    assert "-h" in argv and argv[argv.index("-h") + 1] == "mydb"
    assert "-p" in argv and argv[argv.index("-p") + 1] == "5433"
    assert "-U" in argv and argv[argv.index("-U") + 1] == "admin"


# ---------------------------------------------------------------------------
# FakeProcess for ConnectivityProbe
# ---------------------------------------------------------------------------


class FakeProbeProcess:
    def __init__(self, returncode: int = 0, stdout_data: bytes = b"") -> None:
        self._returncode = returncode
        self._stdout_data = stdout_data
        self.stdout: Any = self

    async def read(self) -> bytes:
        return self._stdout_data

    async def wait(self) -> int:
        return self._returncode

    @property
    def returncode(self) -> int:
        return self._returncode


class TestConnectivityProbe:
    @pytest.fixture()
    def job(self) -> Any:
        return DumpJobFactory.build(service="kenku-pg", host="kenku-pg", port=5432, user="kenku")

    @pytest.fixture()
    def ok_process(self) -> FakeProbeProcess:
        return FakeProbeProcess(returncode=0, stdout_data=b"kenku-pg:5432 - accepting connections")

    @pytest.fixture()
    def fail_process(self) -> FakeProbeProcess:
        return FakeProbeProcess(returncode=2, stdout_data=b"kenku-pg:5432 - no response")

    @pytest.fixture()
    def subject_ok(self, ok_process: FakeProbeProcess) -> ConnectivityProbe:
        async def factory(*args: Any, **kwargs: Any) -> FakeProbeProcess:
            return ok_process

        return ConnectivityProbe(process_factory=factory)

    @pytest.fixture()
    def subject_fail(self, fail_process: FakeProbeProcess) -> ConnectivityProbe:
        async def factory(*args: Any, **kwargs: Any) -> FakeProbeProcess:
            return fail_process

        return ConnectivityProbe(process_factory=factory)

    async def test_ok_when_exit_zero(self, subject_ok: ConnectivityProbe, job: Any) -> None:
        result = await subject_ok.check(job)
        assert result.ok is True
        assert isinstance(result, ProbeResult)

    async def test_detail_contains_stdout_on_success(
        self, subject_ok: ConnectivityProbe, job: Any
    ) -> None:
        result = await subject_ok.check(job)
        assert "accepting connections" in result.detail

    async def test_fail_when_nonzero_exit(self, subject_fail: ConnectivityProbe, job: Any) -> None:
        result = await subject_fail.check(job)
        assert result.ok is False

    async def test_detail_contains_stdout_on_failure(
        self, subject_fail: ConnectivityProbe, job: Any
    ) -> None:
        result = await subject_fail.check(job)
        assert "no response" in result.detail

    async def test_file_not_found_returns_not_ok(self, job: Any) -> None:
        async def factory(*args: Any, **kwargs: Any) -> FakeProbeProcess:
            raise FileNotFoundError("pg_isready not found")

        probe = ConnectivityProbe(process_factory=factory)
        result = await probe.check(job)
        assert result.ok is False
        assert "pg_isready" in result.detail
