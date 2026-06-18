from __future__ import annotations

import asyncio

import pytest

from fiber.services.worker_pool import WorkerPool


class TestWorkerPool:
    @pytest.fixture()
    def subject(self) -> WorkerPool:
        return WorkerPool(max_concurrent=2)

    async def test_skips_overlap_for_same_service(self, subject: WorkerPool) -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def work() -> str:
            started.set()
            await release.wait()
            return "done"

        first = subject.submit("kenku-pg", work)
        await started.wait()
        assert subject.submit("kenku-pg", work) is None  # already running -> skipped
        release.set()
        assert await first == "done"

    async def test_respects_concurrency_cap(self, subject: WorkerPool) -> None:
        active = 0
        peak = 0
        gate = asyncio.Event()

        async def work() -> None:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await gate.wait()
            active -= 1

        tasks = [subject.submit(f"svc{i}", work) for i in range(4)]
        await asyncio.sleep(0.05)
        assert peak <= 2
        gate.set()
        await asyncio.gather(*[t for t in tasks if t is not None])

    async def test_cancel_removes_running_service(self, subject: WorkerPool) -> None:
        started = asyncio.Event()
        release = asyncio.Event()

        async def work() -> None:
            started.set()
            await release.wait()

        task = subject.submit("kenku-pg", work)
        await started.wait()
        assert "kenku-pg" in subject.running_services()
        assert subject.cancel("kenku-pg") is True
        # task is cancelled — wait a moment for cleanup
        await asyncio.sleep(0)
        release.set()

    def test_cancel_returns_false_for_unknown_service(self, subject: WorkerPool) -> None:
        assert subject.cancel("not-running") is False

    def test_running_services_empty_initially(self, subject: WorkerPool) -> None:
        assert subject.running_services() == set()
