from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fiber.models import DumpFormat, DumpJob, Engine

_FORMAT_FLAG = {DumpFormat.CUSTOM: "c", DumpFormat.DIRECTORY: "d", DumpFormat.PLAIN: "p"}


@dataclass(frozen=True)
class RunOutcome:
    returncode: int
    stderr_tail: str
    cancelled: bool


def select_pg_dump_binary(bindir: str = "/usr/lib/postgresql") -> str:
    """Return the pg_dump binary for the highest installed major version, or 'pg_dump' if none."""
    majors: list[int] = []
    try:
        for entry in os.scandir(bindir):
            if entry.is_dir():
                try:
                    majors.append(int(entry.name))
                except ValueError:
                    pass
    except FileNotFoundError:
        pass
    if not majors:
        return "pg_dump"
    max_major = max(majors)
    return f"{bindir}/{max_major}/bin/pg_dump"


def build_pg_dump_argv(job: DumpJob, out_path: str, binary: str = "pg_dump") -> list[str]:
    if job.engine is not Engine.POSTGRES:
        raise NotImplementedError("only postgres in M1")
    argv = [binary, "-h", job.host, "-p", str(job.port), "-U", job.user,
            "-d", job.dbname, "-F", _FORMAT_FLAG[job.fmt]]
    if job.fmt is DumpFormat.DIRECTORY and job.jobs > 1:
        argv += ["-j", str(job.jobs)]
    argv += list(job.options)
    argv += ["-f", out_path]
    return argv


class DumpRunner:
    """Streams pg_dump straight to disk (-f); the dump body never enters this process."""

    def __init__(
        self,
        pg_dump_binary: str | None = None,
        process_factory: Callable[..., Awaitable[asyncio.subprocess.Process]] | None = None,
    ) -> None:
        self._binary = pg_dump_binary if pg_dump_binary is not None else select_pg_dump_binary()
        self._process_factory: Callable[..., Awaitable[Any]] = (
            process_factory if process_factory is not None else asyncio.create_subprocess_exec
        )

    async def run(self, job: DumpJob, password: str, out_path: str) -> RunOutcome:
        env = {**os.environ, "PGPASSWORD": password}
        argv = build_pg_dump_argv(job, out_path, binary=self._binary)
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
