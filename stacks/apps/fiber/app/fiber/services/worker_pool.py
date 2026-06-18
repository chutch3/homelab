from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")


class WorkerPool:
    def __init__(
        self, max_concurrent: int, now: Callable[[], datetime] | None = None
    ) -> None:
        self._sem = asyncio.Semaphore(max_concurrent)
        self._running: dict[str, asyncio.Task[object]] = {}
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._since: dict[str, datetime] = {}

    def submit(self, service: str, work: Callable[[], Awaitable[T]]) -> asyncio.Task[T] | None:
        if service in self._running:
            return None
        self._since[service] = self._now()
        task: asyncio.Task[T] = asyncio.create_task(self._guarded(service, work))
        self._running[service] = task
        return task

    async def _guarded(self, service: str, work: Callable[[], Awaitable[T]]) -> T:
        async with self._sem:
            try:
                return await work()
            finally:
                self._running.pop(service, None)
                self._since.pop(service, None)

    def cancel(self, service: str) -> bool:
        task = self._running.get(service)
        if task is None:
            return False
        task.cancel()
        return True

    def running_services(self) -> set[str]:
        return set(self._running)

    def started_at(self, service: str) -> datetime | None:
        return self._since.get(service)
