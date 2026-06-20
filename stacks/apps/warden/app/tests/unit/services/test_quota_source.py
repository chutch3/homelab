import pytest

from warden.models import ArrType, SourceQuota
from warden.services.quota_source import FallbackQuotaSource, ProwlarrQuotaSource
from tests.factories import indexer, prowlarr_app


class FakeProwlarr:
    def __init__(self, apps, indexers):
        self._apps = apps
        self._indexers = indexers

    async def get_apps(self):
        return list(self._apps)

    async def get_indexers(self):
        return list(self._indexers)


class TestFallbackQuotaSource:
    @pytest.fixture()
    def subject(self) -> FallbackQuotaSource:
        return FallbackQuotaSource()

    async def test_returns_empty_mapping(self, subject: FallbackQuotaSource):
        assert await subject.quotas() == {}


class TestProwlarrQuotaSource:
    @pytest.fixture()
    def make(self):
        def _make(apps, indexers, default=100):
            return ProwlarrQuotaSource(FakeProwlarr(apps, indexers), default_query_limit=default)
        return _make

    async def test_maps_radarr_app_to_min_effective_cap(self, make):
        apps = [prowlarr_app(implementation="Radarr", tags=(1,), sync_categories=(2000,))]
        indexers = [indexer(id=1, query_limit=20), indexer(id=2, query_limit=None)]  # None -> 100 default
        q = (await make(apps, indexers).quotas())[ArrType.RADARR]
        assert q.gross_limit == 20  # bound by the most-constrained indexer
        assert q.mode == "prowlarr"
        assert q.indexers_total == 2
        assert q.indexers_defaulted == 1

    async def test_ignores_unknown_app_implementations(self, make):
        apps = [prowlarr_app(implementation="Mylar", tags=(2,), sync_categories=(7030,))]
        indexers = [indexer(id=1, tags=(2,), categories=(7030,), query_limit=10)]
        assert await make(apps, indexers).quotas() == {}

    async def test_source_with_no_matching_indexers_is_zero(self, make):
        apps = [prowlarr_app(implementation="Sonarr", tags=(1,), sync_categories=(5000,))]
        indexers = [indexer(id=1, tags=(1,), categories=(2000,), query_limit=20)]
        q = (await make(apps, indexers).quotas())[ArrType.SONARR]
        assert q.gross_limit == 0
        assert q.indexers_total == 0
        assert q.mode == "prowlarr"
