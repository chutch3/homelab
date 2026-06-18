import asyncio

from warden.loop import _hunt_loop
from warden.models import SleepDecision


class _OneShotOrch:
    def __init__(self, stop: asyncio.Event) -> None:
        self._stop = stop
        self.ticks = 0

    async def tick(self) -> SleepDecision:
        self.ticks += 1
        self._stop.set()
        return SleepDecision(seconds=0.01, reason="paced")


class _BoomOrch:
    def __init__(self, stop: asyncio.Event) -> None:
        self._stop = stop
        self.ticks = 0

    async def tick(self) -> SleepDecision:
        self.ticks += 1
        self._stop.set()
        raise RuntimeError("boom")


class TestHuntLoop:
    async def test_runs_tick_then_stops(self):
        stop = asyncio.Event()
        orch = _OneShotOrch(stop)
        await _hunt_loop(stop, orchestrator=orch)
        assert orch.ticks == 1

    async def test_survives_tick_exception(self):
        stop = asyncio.Event()
        orch = _BoomOrch(stop)
        await _hunt_loop(stop, orchestrator=orch)  # must not raise
        assert orch.ticks == 1
