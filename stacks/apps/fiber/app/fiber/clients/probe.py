from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from fiber.clients.engines import DumpEngine, build_default_engines
from fiber.domain.models import DumpJob, Engine


@dataclass(frozen=True)
class ProbeResult:
    ok: bool
    detail: str


class ConnectivityProbe:
    """Runs the engine's reachability probe. Engine-specific argv lives in the DumpEngine
    strategies; this class only spawns the probe process via an injected factory."""

    def __init__(
        self,
        engines: Mapping[Engine, DumpEngine] | None = None,
        process_factory: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self._engines = engines if engines is not None else build_default_engines()
        self._process_factory: Callable[..., Awaitable[Any]] = (
            process_factory if process_factory is not None else asyncio.create_subprocess_exec
        )

    async def check(self, job: DumpJob) -> ProbeResult:
        argv = self._engines[job.engine].probe_argv(job)
        try:
            proc = await self._process_factory(
                *argv,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
        except FileNotFoundError as exc:
            return ProbeResult(ok=False, detail=f"probe binary not found: {exc}")

        stdout_data = await proc.stdout.read()  # type: ignore[union-attr]
        await proc.wait()
        detail = stdout_data.decode(errors="replace").strip()
        ok = proc.returncode == 0
        return ProbeResult(ok=ok, detail=detail)
