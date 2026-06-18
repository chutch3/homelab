from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from warden.models import ArrType, WantedItem, WantKind


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
                       title=r.get("title", ""), kind=kind)
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
