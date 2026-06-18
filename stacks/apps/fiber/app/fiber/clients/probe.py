from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fiber.models import DumpJob


def build_pg_isready_argv(job: DumpJob) -> list[str]:
    """Return the argv for pg_isready for the given job."""
    return ["pg_isready", "-h", job.host, "-p", str(job.port), "-U", job.user]


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    detail: str


class ConnectivityProbe:
    """Runs pg_isready to check reachability. Uses an injected process_factory for testability."""

    def __init__(
        self,
        process_factory: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self._process_factory: Callable[..., Awaitable[Any]] = (
            process_factory if process_factory is not None else asyncio.create_subprocess_exec
        )

    async def check(self, job: DumpJob) -> ProbeResult:
        argv = build_pg_isready_argv(job)
        try:
            proc = await self._process_factory(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            return ProbeResult(ok=False, detail=f"pg_isready not found: {exc}")

        stdout_data = await proc.stdout.read()  # type: ignore[union-attr]
        await proc.wait()
        detail = stdout_data.decode(errors="replace").strip()
        ok = proc.returncode == 0
        return ProbeResult(ok=ok, detail=detail)
