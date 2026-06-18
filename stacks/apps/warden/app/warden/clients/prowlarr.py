from __future__ import annotations

import httpx

from warden.models import Indexer, ProwlarrApp


def _normalize_query_limit(query_limit: int | None, limits_unit: int) -> int | None:
    """Normalize a Prowlarr query limit to per-day. limitsUnit: 0=day, 1=hour."""
    if query_limit is None:
        return None
    return query_limit * 24 if limits_unit == 1 else query_limit


class ProwlarrClient:
    """Owned abstraction over the Prowlarr v1 API (apps + indexers)."""

    def __init__(self, base_url: str, http: httpx.AsyncClient, api_key: str) -> None:
        self._base = base_url.rstrip("/")
        self._http = http
        self._headers = {"X-Api-Key": api_key}

    async def _get(self, path: str) -> list[dict]:
        resp = await self._http.get(f"{self._base}{path}", headers=self._headers)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _fields(obj: dict) -> dict:
        return {f.get("name"): f.get("value") for f in obj.get("fields", [])}

    async def get_apps(self) -> list[ProwlarrApp]:
        apps: list[ProwlarrApp] = []
        for a in await self._get("/api/v1/applications"):
            fields = self._fields(a)
            cats = fields.get("syncCategories") or []
            apps.append(ProwlarrApp(
                implementation=a.get("implementation", ""),
                tags=tuple(a.get("tags", []) or []),
                sync_categories=tuple(int(c) for c in cats),
            ))
        return apps

    async def get_indexers(self) -> list[Indexer]:
        indexers: list[Indexer] = []
        for i in await self._get("/api/v1/indexer"):
            fields = self._fields(i)
            cats = [int(c["id"]) for c in (i.get("capabilities", {}) or {}).get("categories", [])]
            indexers.append(Indexer(
                id=int(i["id"]),
                name=i.get("name", ""),
                enabled=bool(i.get("enable", False)),
                tags=tuple(i.get("tags", []) or []),
                categories=tuple(cats),
                query_limit=_normalize_query_limit(
                    fields.get("baseSettings.queryLimit"),
                    int(fields.get("baseSettings.limitsUnit") or 0),
                ),
            ))
        return indexers
