from __future__ import annotations

import asyncio


class EventBroker:
    def __init__(self) -> None:
        self.subscribers: set[asyncio.Queue[str]] = set()

    def subscribe(self) -> asyncio.Queue[str]:
        q: asyncio.Queue[str] = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[str]) -> None:
        self.subscribers.discard(q)

    async def publish(self, service: str) -> None:
        for q in list(self.subscribers):
            await q.put(service)
