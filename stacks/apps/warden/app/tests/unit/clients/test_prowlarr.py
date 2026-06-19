import pytest
import httpx

from warden.clients.prowlarr import ProwlarrClient


def transport(handler):
    return httpx.MockTransport(handler)


APPS = [
    {"name": "Radarr", "implementation": "Radarr", "tags": [2, 1],
     "fields": [{"name": "syncCategories", "value": [2000, 2010, 2040]}]},
    {"name": "Sonarr", "implementation": "Sonarr", "tags": [1],
     "fields": [{"name": "syncCategories", "value": [5000, 5010]}]},
]
INDEXERS = [
    {"id": 7, "name": "YTS", "enable": True, "protocol": "torrent", "tags": [1],
     "capabilities": {"categories": [{"id": 2000, "name": "Movies"}, {"id": 2040, "name": "HD"}]},
     "fields": [{"name": "baseSettings.queryLimit", "value": 20},
                {"name": "baseSettings.grabLimit", "value": 5},
                {"name": "baseSettings.limitsUnit", "value": 0}]},
    {"id": 8, "name": "Unlimited", "enable": True, "protocol": "torrent", "tags": [1],
     "capabilities": {"categories": [{"id": 5000, "name": "TV"}]},
     "fields": [{"name": "baseSettings.queryLimit", "value": None},
                {"name": "baseSettings.limitsUnit", "value": 0}]},
    {"id": 9, "name": "Hourly", "enable": False, "protocol": "torrent", "tags": [2],
     "capabilities": {"categories": [{"id": 2000, "name": "Movies"}]},
     "fields": [{"name": "baseSettings.queryLimit", "value": 5},
                {"name": "baseSettings.limitsUnit", "value": 1}]},
]


def make_client() -> ProwlarrClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/v1/applications":
            assert request.headers["X-Api-Key"] == "pk"
            return httpx.Response(200, json=APPS)
        if request.url.path == "/api/v1/indexer":
            return httpx.Response(200, json=INDEXERS)
        return httpx.Response(404)
    return ProwlarrClient(base_url="http://prowlarr:9696",
                          http=httpx.AsyncClient(transport=transport(handler)), api_key="pk")


class TestProwlarrClient:
    @pytest.fixture()
    def subject(self) -> ProwlarrClient:
        return make_client()

    async def test_get_apps_parses_impl_tags_and_sync_categories(self, subject):
        apps = await subject.get_apps()
        radarr = next(a for a in apps if a.implementation == "Radarr")
        assert radarr.tags == (2, 1)
        assert radarr.sync_categories == (2000, 2010, 2040)

    async def test_get_indexers_parses_enable_tags_categories_and_querylimit(self, subject):
        idx = {i.name: i for i in await subject.get_indexers()}
        assert idx["YTS"].enabled is True
        assert idx["YTS"].tags == (1,)
        assert idx["YTS"].categories == (2000, 2040)
        assert idx["YTS"].query_limit == 20

    async def test_none_query_limit_preserved_as_none(self, subject):
        idx = {i.name: i for i in await subject.get_indexers()}
        assert idx["Unlimited"].query_limit is None

    async def test_hourly_unit_normalized_to_per_day(self, subject):
        idx = {i.name: i for i in await subject.get_indexers()}
        # 5/hour * 24 = 120/day
        assert idx["Hourly"].query_limit == 120
        assert idx["Hourly"].enabled is False
