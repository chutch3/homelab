import asyncio
import os
import time
from typing import Awaitable, Callable, Optional


class DownloadProgressTracker:
    def __init__(
        self,
        interval: float = 2.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.interval = interval
        self._clock = clock

    async def track(
        self,
        path: str,
        total_bytes: Optional[int],
        on_progress: Callable[[int, Optional[int], float], Awaitable[None]],
        stop_event: asyncio.Event,
    ) -> None:
        last_bytes = 0
        last_time = self._clock()

        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self.interval)
            except asyncio.TimeoutError:
                pass
            if stop_event.is_set():
                break

            current_bytes = os.path.getsize(path) if os.path.exists(path) else 0
            now = self._clock()
            elapsed = now - last_time
            speed = (current_bytes - last_bytes) / elapsed if elapsed > 0 else 0.0

            await on_progress(current_bytes, total_bytes, speed)

            last_bytes = current_bytes
            last_time = now
