from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from warden.models import ArrType, QueueItem, WantedItem, WantKind


def _parse_iso(raw: str | None) -> datetime | None:
    """Parse an *arr ISO-8601 `...Z` timestamp to aware UTC; None when null/absent."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None


def _parse_added(raw: str | None) -> datetime:
    return _parse_iso(raw) or datetime(1970, 1, 1, tzinfo=timezone.utc)


class ArrClient(ABC):
    """Owned abstraction over a Servarr v3 instance (Radarr/Sonarr share the API shape)."""

    def __init__(self, name: str, base_url: str, http: httpx.AsyncClient, api_key: str) -> None:
        self.name = name
        self._base = base_url.rstrip("/")
        self._http = http
        self._headers = {"X-Api-Key": api_key}

    @property
    @abstractmethod
    def arr_type(self) -> ArrType: ...

    @property
    @abstractmethod
    def _search_command(self) -> str: ...

    @property
    @abstractmethod
    def _id_field(self) -> str: ...

    @property
    @abstractmethod
    def _queue_id_field(self) -> str: ...

    async def _wanted(self, endpoint: str, kind: WantKind) -> list[WantedItem]:
        resp = await self._http.get(
            f"{self._base}/api/v3/wanted/{endpoint}",
            headers=self._headers,
            params={"pageSize": 1000},
        )
        resp.raise_for_status()
        records = resp.json().get("records", [])
        return [
            WantedItem(instance=self.name, remote_id=int(r["id"]),
                       title=r.get("title", ""), kind=kind,
                       last_search_time=_parse_iso(r.get("lastSearchTime")))
            for r in records
        ]

    async def list_missing(self) -> list[WantedItem]:
        return await self._wanted("missing", WantKind.MISSING)

    async def list_cutoff_unmet(self) -> list[WantedItem]:
        return await self._wanted("cutoff", WantKind.CUTOFF_UNMET)

    async def trigger_search(self, ids: list[int]) -> None:
        if not ids:
            return
        resp = await self._http.post(
            f"{self._base}/api/v3/command",
            headers=self._headers,
            json={"name": self._search_command, self._id_field: ids},
        )
        resp.raise_for_status()

    async def list_queue(self) -> list[QueueItem]:
        resp = await self._http.get(
            f"{self._base}/api/v3/queue", headers=self._headers, params={"pageSize": 1000})
        resp.raise_for_status()
        records = resp.json().get("records", [])
        return [
            QueueItem(
                id=int(r["id"]),
                remote_id=int(r.get(self._queue_id_field) or 0),
                title=r.get("title", ""),
                status=r.get("status", ""),
                error_message=r.get("errorMessage") or "",
                added=_parse_added(r.get("added")),
            )
            for r in records
        ]

    async def remove_queue_item(self, queue_id: int, *, remove_from_client: bool = True,
                                blocklist: bool = True) -> None:
        resp = await self._http.delete(
            f"{self._base}/api/v3/queue/{queue_id}", headers=self._headers,
            params={"removeFromClient": str(remove_from_client).lower(),
                    "blocklist": str(blocklist).lower()})
        resp.raise_for_status()


class RadarrClient(ArrClient):
    @property
    def arr_type(self) -> ArrType:
        return ArrType.RADARR

    @property
    def _search_command(self) -> str:
        return "MoviesSearch"

    @property
    def _id_field(self) -> str:
        return "movieIds"

    @property
    def _queue_id_field(self) -> str:
        return "movieId"


class SonarrClient(ArrClient):
    @property
    def arr_type(self) -> ArrType:
        return ArrType.SONARR

    @property
    def _search_command(self) -> str:
        return "EpisodeSearch"

    @property
    def _id_field(self) -> str:
        return "episodeIds"

    @property
    def _queue_id_field(self) -> str:
        return "episodeId"
