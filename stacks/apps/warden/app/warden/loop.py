from __future__ import annotations

import asyncio
import contextlib

from dependency_injector.wiring import Provide, inject

from warden.container import Container
from warden.logger import get_logger
from warden.services.orchestrator import TickOrchestrator

_logger = get_logger("warden.loop")


@inject
async def _hunt_loop(
    stop: asyncio.Event,
    orchestrator: TickOrchestrator = Provide[Container.orchestrator],
) -> None:
    while not stop.is_set():
        try:
            decision = await orchestrator.tick()
            sleep_for = decision.seconds
        except Exception:  # noqa: BLE001 - keep the loop alive
            _logger.exception("tick failed", extra={"event": "tick_error"})
            sleep_for = 60.0
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=max(1.0, sleep_for))
