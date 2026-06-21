from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol


class ArrType(str, Enum):
    RADARR = "radarr"
    SONARR = "sonarr"


class WantKind(str, Enum):
    MISSING = "missing"
    CUTOFF_UNMET = "cutoff_unmet"


@dataclass(frozen=True)
class InstanceConfig:
    name: str
    type: ArrType
    url: str
    api_key: str


@dataclass(frozen=True)
class WantedItem:
    instance: str
    remote_id: int          # movieId (radarr) or episodeId (sonarr)
    title: str
    kind: WantKind
    last_search_time: datetime | None = None   # *arr lastSearchTime; None = never searched


@dataclass(frozen=True)
class QueueItem:
    id: int                 # queue record id — used in the DELETE
    remote_id: int          # movieId (radarr) / episodeId (sonarr) — for hunt-exclusion
    title: str
    status: str             # top-level queue status (e.g. "downloading", "warning", "downloadClientUnavailable")
    error_message: str      # top-level errorMessage ("" when null) — carries the stall reason
    added: datetime         # aware UTC
    download_id: str = ""   # client hash; "" when absent (downloadClientUnavailable)
    size_left: int = 0      # bytes remaining (for no-progress detection)


@dataclass(frozen=True)
class Anchor:
    """No-progress checkpoint: a download's bytes-remaining at a point in time."""
    size_left: int
    at: datetime


@dataclass(frozen=True)
class GrabEvent:
    """A grab recorded in *arr history (eventType=grabbed)."""
    remote_id: int          # movieId (radarr) / episodeId (sonarr)
    indexer: str            # data.indexer, e.g. "EZTVL (Prowlarr)"
    at: datetime            # grab time (aware UTC)
    release_source: str = ""  # data.releaseSource (UserInvokedSearch/Search/Rss/...)


@dataclass(frozen=True)
class SearchAttempt:
    """A search warden fired, awaiting reconciliation against grabs."""
    remote_id: int
    kind: str               # WantKind value
    searched_at: datetime   # aware UTC


@dataclass(frozen=True)
class InstanceWanted:
    missing: tuple[WantedItem, ...]
    cutoff_unmet: tuple[WantedItem, ...]


@dataclass(frozen=True)
class QuotaState:
    daily_budget: int
    spent: int
    remaining: int
    blocked: bool
    reset_at: datetime


@dataclass(frozen=True)
class SleepDecision:
    seconds: float          # how long the loop should sleep before the next tick
    reason: str             # "paced" | "blocked"


@dataclass(frozen=True)
class ProwlarrApp:
    implementation: str          # "Radarr" | "Sonarr" | ...
    tags: tuple[int, ...]
    sync_categories: tuple[int, ...]


@dataclass(frozen=True)
class Indexer:
    id: int
    name: str
    enabled: bool
    tags: tuple[int, ...]
    categories: tuple[int, ...]
    query_limit: int | None      # normalized to per-day; None = no Prowlarr limit


@dataclass(frozen=True)
class SourceQuota:
    gross_limit: int          # max effective per-indexer daily query cap (pre-reserve) = the binding limit
    mode: str                 # "prowlarr"
    indexers_total: int       # synced indexers considered for this source
    indexers_defaulted: int   # of those, how many had NO Prowlarr limit (default cap applied)


class ArrClientProtocol(Protocol):
    """Structural interface the orchestrator depends on (RadarrClient/SonarrClient and
    the test double satisfy it without inheritance)."""

    name: str
    arr_type: "ArrType"

    async def list_missing(self) -> list[WantedItem]: ...
    async def list_cutoff_unmet(self) -> list[WantedItem]: ...
    async def trigger_search(self, ids: list[int]) -> None: ...
    async def list_queue(self) -> list["QueueItem"]: ...
    async def remove_queue_item(self, queue_id: int, *, remove_from_client: bool = True,
                                blocklist: bool = True) -> None: ...
    async def list_grabbed_since(self, since: datetime) -> list["GrabEvent"]: ...


class ProwlarrReader(Protocol):
    """Structural interface for reading Prowlarr (ProwlarrClient and the test
    double satisfy it without inheritance)."""

    async def get_apps(self) -> list[ProwlarrApp]: ...
    async def get_indexers(self) -> list[Indexer]: ...


class QuotaSource(Protocol):
    """Yields each source's quota provenance (empty mapping => caller
    uses its flat fallback budget)."""

    async def quotas(self) -> dict["ArrType", "SourceQuota"]: ...
