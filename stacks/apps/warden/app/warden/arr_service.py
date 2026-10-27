from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from warden.clients.arr import ArrClient


class ArrService:
    """Read profile configuration through the application's configured Arr clients."""

    def __init__(self, clients: Mapping[str, ArrClient]) -> None:
        self.clients = dict(clients)

    @property
    def sources(self) -> tuple[str, ...]:
        return tuple(self.clients)

    async def get_profiles(self, source: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if source not in self.clients:
            prefix = f"WARDEN_{source.upper()}"
            raise ValueError(f"{prefix}_URL and {prefix}_API_KEY are required")
        client = self.clients[source]
        return await client.list_quality_profiles(), await client.list_custom_formats()
