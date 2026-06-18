from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime

from fiber.models import DumpJob, MisconfiguredJob


@dataclass(frozen=True)
class Snapshot:
    jobs: list[DumpJob] = field(default_factory=list)
    misconfigured: list[MisconfiguredJob] = field(default_factory=list)
    skipped: list[tuple[str, str]] = field(default_factory=list)  # (service, reason)
    scanned_at: datetime | None = None
    error: str | None = None


class RegistryState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._snap = Snapshot()

    def set(self, snap: Snapshot) -> None:
        with self._lock:
            self._snap = snap

    def get(self) -> Snapshot:
        with self._lock:
            return self._snap
