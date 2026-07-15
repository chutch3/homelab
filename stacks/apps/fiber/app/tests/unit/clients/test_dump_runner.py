from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any

import pytest

from fiber.clients.dump_runner import DumpRunner, RunOutcome
from fiber.domain.models import DumpJob
from tests.factories import DumpJobFactory, MysqlDumpJobFactory


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
# DumpRunner orchestration (engine-agnostic: process, timeout, cancel)
# ---------------------------------------------------------------------------

class TestDumpRunner:
    @pytest.fixture()
    def fake_proc(self) -> FakeProcess:
        return FakeProcess(returncode=0, stderr_data=b"")

    @pytest.fixture()
    def subject(self, fake_proc: FakeProcess) -> DumpRunner:
        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return fake_proc
        return DumpRunner(process_factory=factory)

    async def test_success_returns_zero_returncode(
        self, subject: DumpRunner, fake_proc: FakeProcess
    ) -> None:
        outcome = await subject.run(_make_job(), password="pw", out_path="/bowl/x.dump")
        assert outcome == RunOutcome(returncode=0, stderr_tail="", cancelled=False)

    async def test_failure_captures_stderr_tail(self) -> None:
        proc = FakeProcess(returncode=1, stderr_data=b"boom")

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return proc

        runner = DumpRunner(process_factory=factory)
        outcome = await runner.run(_make_job(), password="pw", out_path="/bowl/x.dump")
        assert outcome.returncode == 1
        assert outcome.cancelled is False
        assert "boom" in outcome.stderr_tail

    async def test_timeout_cancels_and_terminates(self) -> None:
        proc = FakeProcess(returncode=0, hang=True)

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return proc

        runner = DumpRunner(process_factory=factory)
        outcome = await runner.run(_make_job(timeout=0.01), password="pw", out_path="/bowl/x.dump")
        assert outcome.cancelled is True
        assert proc.terminated is True

    async def test_external_cancel_cancels_and_terminates(self) -> None:
        proc = FakeProcess(returncode=0, hang=True)

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return proc

        runner = DumpRunner(process_factory=factory)

        async def _run() -> RunOutcome:
            return await runner.run(_make_job(), password="pw", out_path="/bowl/x.dump")

        task = asyncio.create_task(_run())
        await asyncio.sleep(0.01)
        task.cancel()
        outcome = await task
        assert outcome.cancelled is True
        assert proc.terminated is True


# ---------------------------------------------------------------------------
# Engine dispatch + credentials-file lifecycle
# ---------------------------------------------------------------------------

class TestDumpRunnerEngineDispatch:
    async def test_postgres_sets_pgpassword_and_writes_no_creds_file(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        captured: dict[str, Any] = {}

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            captured["argv"], captured["env"] = args, kwargs["env"]
            return FakeProcess(returncode=0)

        runner = DumpRunner(process_factory=factory)
        await runner.run(DumpJobFactory.build(timeout=None), password="pw",
                         out_path=str(tmp_path / "x.dump"))

        assert captured["env"]["PGPASSWORD"] == "pw"
        assert not any("defaults-extra-file" in a for a in captured["argv"])
        assert list(tmp_path.glob("*.cnf")) == []

    async def test_mysql_password_only_in_creds_file_never_argv_or_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        captured: dict[str, Any] = {}

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            creds = next(a.split("=", 1)[1] for a in args
                         if a.startswith("--defaults-extra-file="))
            captured["argv"], captured["env"] = args, kwargs["env"]
            captured["creds_path"] = creds
            captured["creds_content"] = Path(creds).read_text()
            captured["mode"] = oct(os.stat(creds).st_mode & 0o777)
            return FakeProcess(returncode=0)

        runner = DumpRunner(process_factory=factory)
        outcome = await runner.run(MysqlDumpJobFactory.build(timeout=None),
                                   password="s3cr3t", out_path=str(tmp_path / "x.sql"))

        assert outcome.returncode == 0
        assert "password=s3cr3t" in captured["creds_content"]
        assert captured["mode"] == "0o600"
        assert "s3cr3t" not in " ".join(captured["argv"])
        assert "s3cr3t" not in repr(captured["env"])
        assert "PGPASSWORD" not in captured["env"]
        # unlinked on success
        assert not os.path.exists(captured["creds_path"])
        assert list(tmp_path.glob("*.cnf")) == []

    async def test_mysql_creds_unlinked_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return FakeProcess(returncode=1, stderr_data=b"boom")

        runner = DumpRunner(process_factory=factory)
        outcome = await runner.run(MysqlDumpJobFactory.build(timeout=None),
                                   password="pw", out_path=str(tmp_path / "x.sql"))
        assert outcome.returncode == 1
        assert list(tmp_path.glob("*.cnf")) == []

    async def test_mysql_creds_unlinked_on_timeout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TMPDIR", str(tmp_path))

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return FakeProcess(returncode=0, hang=True)

        runner = DumpRunner(process_factory=factory)
        outcome = await runner.run(MysqlDumpJobFactory.build(timeout=0.01),
                                   password="pw", out_path=str(tmp_path / "x.sql"))
        assert outcome.cancelled is True
        assert list(tmp_path.glob("*.cnf")) == []

    async def test_mysql_creds_unlinked_on_external_cancel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        proc = FakeProcess(returncode=0, hang=True)

        async def factory(*args: Any, **kwargs: Any) -> FakeProcess:
            return proc

        runner = DumpRunner(process_factory=factory)

        async def _run() -> RunOutcome:
            return await runner.run(MysqlDumpJobFactory.build(timeout=None),
                                    password="pw", out_path=str(tmp_path / "x.sql"))

        task = asyncio.create_task(_run())
        await asyncio.sleep(0.01)
        task.cancel()
        outcome = await task
        assert outcome.cancelled is True
        assert list(tmp_path.glob("*.cnf")) == []
