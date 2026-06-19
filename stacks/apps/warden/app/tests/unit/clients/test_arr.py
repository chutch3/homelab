import json
from datetime import timezone

import httpx

from warden.clients.arr import RadarrClient, SonarrClient
from warden.models import WantKind


def transport(handler):
    return httpx.MockTransport(handler)


class TestRadarrClient:
    async def test_list_missing_maps_movie_ids(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v3/wanted/missing"
            assert request.headers["X-Api-Key"] == "rk"
            return httpx.Response(200, json={"records": [
                {"id": 11, "title": "Dune"}, {"id": 12, "title": "Heat"}]})

        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        items = await client.list_missing()
        assert [(i.remote_id, i.title, i.kind) for i in items] == [
            (11, "Dune", WantKind.MISSING), (12, "Heat", WantKind.MISSING)]

    async def test_trigger_search_posts_movies_search_command(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["body"] = json.loads(request.content)
            return httpx.Response(201, json={"id": 1})

        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        await client.trigger_search([11, 12])
        assert seen["path"] == "/api/v3/command"
        assert seen["body"] == {"name": "MoviesSearch", "movieIds": [11, 12]}

    async def test_list_cutoff_unmet_hits_cutoff_endpoint(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v3/wanted/cutoff"
            return httpx.Response(200, json={"records": [{"id": 7, "title": "X"}]})

        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        items = await client.list_cutoff_unmet()
        assert items[0].remote_id == 7 and items[0].kind == WantKind.CUTOFF_UNMET

    async def test_trigger_search_empty_is_noop(self):
        calls: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            calls.append(request.url.path)
            return httpx.Response(200, json={})

        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        await client.trigger_search([])
        assert calls == []

    def test_radarr_arr_type(self):
        from warden.models import ArrType
        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(lambda r: httpx.Response(200, json={}))),
                              api_key="rk")
        assert client.arr_type == ArrType.RADARR


class TestSonarrClient:
    async def test_trigger_search_posts_episode_search_command(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["body"] = json.loads(request.content)
            return httpx.Response(201, json={"id": 1})

        client = SonarrClient(name="sonarr", base_url="http://sonarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="sk")
        await client.trigger_search([5, 6])
        assert seen["body"] == {"name": "EpisodeSearch", "episodeIds": [5, 6]}


class TestRadarrQueue:
    async def test_list_queue_maps_records(self):
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/v3/queue"
            return httpx.Response(200, json={"records": [
                {"id": 5, "movieId": 11, "title": "Dune", "status": "warning",
                 "errorMessage": "The download is stalled with no connections",
                 "added": "2026-06-15T00:00:00Z"},
                {"id": 6, "movieId": 12, "title": "Heat", "status": "downloading",
                 "errorMessage": None, "added": "2026-06-18T00:00:00Z"},
            ]})
        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        items = await client.list_queue()
        assert [(i.id, i.remote_id, i.status, i.error_message) for i in items] == [
            (5, 11, "warning", "The download is stalled with no connections"),
            (6, 12, "downloading", ""),
        ]
        assert items[0].added.utcoffset() == timezone.utc.utcoffset(None)

    async def test_remove_queue_item_issues_delete_with_params(self):
        seen = {}
        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["params"] = dict(request.url.params)
            seen["method"] = request.method
            return httpx.Response(200, json={})
        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        await client.remove_queue_item(5, remove_from_client=True, blocklist=True)
        assert seen["method"] == "DELETE"
        assert seen["path"] == "/api/v3/queue/5"
        assert seen["params"] == {"removeFromClient": "true", "blocklist": "true"}


class TestSonarrQueue:
    async def test_list_queue_uses_episode_id(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"records": [
                {"id": 7, "episodeId": 99, "title": "S01E01", "status": "warning",
                 "errorMessage": "stalled", "added": "2026-06-15T00:00:00Z"}]})
        client = SonarrClient(name="sonarr", base_url="http://sonarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="sk")
        items = await client.list_queue()
        assert items[0].remote_id == 99
