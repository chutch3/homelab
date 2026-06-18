from __future__ import annotations

from fiber.clients.bowl import BowlStorage
from fiber.repositories.history import HistoryRepository
from fiber.clients.discovery import DiscoveryProvider


class Readiness:
    def __init__(self, bowl: BowlStorage, history: HistoryRepository, swarm: DiscoveryProvider) -> None:
        self._bowl = bowl
        self._history = history
        self._swarm = swarm

    def __call__(self) -> bool:
        try:
            if not self._bowl.has_room(1):
                return False
            self._history.last_success("__healthz__")
            self._swarm.list_dump_services()
            return True
        except Exception:
            return False
