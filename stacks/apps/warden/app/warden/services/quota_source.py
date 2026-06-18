from __future__ import annotations

from warden.models import ArrType, ProwlarrReader, SourceQuota
from warden.services.indexers import indexers_for_app, source_gross_limit


class FallbackQuotaSource:
    """No Prowlarr — caller falls back to its flat per-day budget."""

    async def quotas(self) -> dict[ArrType, SourceQuota]:
        return {}


class ProwlarrQuotaSource:
    """Per-source quota derived from Prowlarr's synced indexers."""

    def __init__(self, client: ProwlarrReader, default_query_limit: int) -> None:
        self._client = client
        self._default = default_query_limit

    async def quotas(self) -> dict[ArrType, SourceQuota]:
        apps = await self._client.get_apps()
        indexers = await self._client.get_indexers()
        out: dict[ArrType, SourceQuota] = {}
        for app in apps:
            try:
                arr_type = ArrType(app.implementation.lower())
            except ValueError:
                continue
            matched = indexers_for_app(app, indexers)
            out[arr_type] = SourceQuota(
                gross_limit=source_gross_limit(matched, self._default),
                mode="prowlarr",
                indexers_total=len(matched),
                indexers_defaulted=sum(1 for i in matched if i.query_limit is None),
            )
        return out
