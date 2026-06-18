from __future__ import annotations

from fiber.clients.bowl import BowlStorage
from fiber.repositories.history import HistoryRepository
from fiber.clients.discovery import DiscoveryProvider


class Readiness:
    def __init__(self, bowl: BowlStorage, history: HistoryRepository, discovery: DiscoveryProvider) -> None:
        self._bowl = bowl
        self._history = history
        self._discovery = discovery

    def __call__(self) -> bool:
        try:
            if not self._bowl.has_room(1):
                return False
            self._history.last_success("__healthz__")
            self._discovery.list_dump_services()
            return True
        except Exception:
            return False
