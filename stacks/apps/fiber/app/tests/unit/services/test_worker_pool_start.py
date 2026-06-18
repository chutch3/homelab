import asyncio
from datetime import datetime, timezone

from fiber.services.worker_pool import WorkerPool


async def test_tracks_started_at() -> None:
    gate = asyncio.Event()
    pool = WorkerPool(
        max_concurrent=1,
        now=lambda: datetime(2026, 6, 15, 3, tzinfo=timezone.utc),
    )
    t = pool.submit("immich", lambda: gate.wait())
    await asyncio.sleep(0.01)
    assert pool.started_at("immich") == datetime(2026, 6, 15, 3, tzinfo=timezone.utc)
    assert pool.started_at("nope") is None
    gate.set()
    await t
    assert pool.started_at("immich") is None
