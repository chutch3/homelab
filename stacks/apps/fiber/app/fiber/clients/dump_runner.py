from __future__ import annotations

import asyncio
import os
import tempfile
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from fiber.clients.engines import DumpEngine, build_default_engines
from fiber.domain.models import DumpJob, Engine


@dataclass(frozen=True)
class RunOutcome:
    returncode: int
    stderr_tail: str
    cancelled: bool


class DumpRunner:
    """Runs an engine's dump command, streaming straight to disk; the dump body never
    enters this process.

    Engine-specific argv/credentials live in the DumpEngine strategies. This class only
    orchestrates: pick the engine, materialise its temp creds file, spawn the process,
    enforce the timeout, and clean up.
    """

    def __init__(
        self,
        engines: Mapping[Engine, DumpEngine] | None = None,
        process_factory: Callable[..., Awaitable[asyncio.subprocess.Process]] | None = None,
    ) -> None:
        self._engines = engines if engines is not None else build_default_engines()
        self._process_factory: Callable[..., Awaitable[Any]] = (
            process_factory if process_factory is not None else asyncio.create_subprocess_exec
        )

    async def run(self, job: DumpJob, password: str, out_path: str) -> RunOutcome:
        engine = self._engines[job.engine]
        creds_path: str | None = None
        try:
            content = engine.credentials_content(password)
            if content is not None:
                creds_path = self._write_creds(content)
            env = {**os.environ, **engine.dump_env(password)}
            argv = engine.build_argv(job, out_path, creds_path)
            proc = await self._process_factory(
                *argv, env=env, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE,
            )
            try:
                if job.timeout:
                    stderr = await asyncio.wait_for(self._wait(proc), timeout=job.timeout)
                else:
                    stderr = await self._wait(proc)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                await self._kill(proc)
                return RunOutcome(returncode=-1, stderr_tail="cancelled", cancelled=True)
            assert proc.returncode is not None
            return RunOutcome(returncode=proc.returncode, stderr_tail=stderr[-4000:], cancelled=False)
        finally:
            if creds_path is not None:
                try:
                    os.unlink(creds_path)
                except FileNotFoundError:
                    pass

    @staticmethod
    def _write_creds(content: str) -> str:
        """Write a 0600 temp creds file (honours $TMPDIR); the caller unlinks it."""
        fd, path = tempfile.mkstemp(suffix=".cnf")  # mkstemp opens with mode 0600
        try:
            os.write(fd, content.encode())
        finally:
            os.close(fd)
        return path

    async def _wait(self, proc: asyncio.subprocess.Process) -> str:
        assert proc.stderr is not None
        data = await proc.stderr.read()
        await proc.wait()
        return data.decode(errors="replace")

    async def _kill(self, proc: asyncio.subprocess.Process) -> None:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=10)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
