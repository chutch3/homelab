from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone

import httpx

from warden.models import ArrType, GrabEvent, QueueItem, WantedItem, WantKind


def _parse_iso(raw: str | None) -> datetime | None:
    """Parse an *arr ISO-8601 `...Z` timestamp to aware UTC; None when null/absent."""
    return datetime.fromisoformat(raw.replace("Z", "+00:00")) if raw else None


def _fmt_iso(when: datetime) -> str:
    """Format an aware datetime as the `...Z` UTC string *arr query params expect."""
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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

    _PAGE_SIZE = 1000

    async def _paged_records(self, endpoint: str) -> list[dict]:
        """Fetch every record from a paginated Servarr v3 list endpoint, walking
        page/pageSize until totalRecords is reached, so large lists aren't truncated."""
        records: list[dict] = []
        page = 1
        while True:
            resp = await self._http.get(
                f"{self._base}/api/v3/{endpoint}",
                headers=self._headers,
                params={"page": page, "pageSize": self._PAGE_SIZE},
            )
            resp.raise_for_status()
            body = resp.json()
            batch = body.get("records", [])
            records.extend(batch)
            total = body.get("totalRecords", len(records))
            if not batch or len(records) >= total:
                break
            page += 1
        return records

    async def _wanted(self, endpoint: str, kind: WantKind) -> list[WantedItem]:
        records = await self._paged_records(f"wanted/{endpoint}")
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
        records = await self._paged_records("queue")
        return [
            QueueItem(
                id=int(r["id"]),
                remote_id=int(r.get(self._queue_id_field) or 0),
                title=r.get("title", ""),
                status=r.get("status", ""),
                error_message=r.get("errorMessage") or "",
                added=_parse_added(r.get("added")),
                download_id=r.get("downloadId") or "",
                size_left=int(r.get("sizeleft") or 0),
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

    async def list_grabbed_since(self, since: datetime) -> list[GrabEvent]:
        resp = await self._http.get(
            f"{self._base}/api/v3/history/since", headers=self._headers,
            params={"date": _fmt_iso(since), "eventType": "grabbed"})
        resp.raise_for_status()
        events = []
        for r in resp.json():
            rid = r.get(self._queue_id_field)
            at = _parse_iso(r.get("date"))
            if rid is None or at is None:
                continue                          # malformed row — skip defensively
            data = r.get("data") or {}
            events.append(GrabEvent(remote_id=int(rid), indexer=data.get("indexer", ""),
                                    at=at, release_source=data.get("releaseSource", "")))
        return events


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
