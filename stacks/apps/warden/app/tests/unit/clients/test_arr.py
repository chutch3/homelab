import json
from datetime import datetime, timezone

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

    async def test_list_missing_paginates_until_total_reached(self):
        seen_pages = []

        def handler(request: httpx.Request) -> httpx.Response:
            page = int(request.url.params.get("page", "1"))
            seen_pages.append(page)
            if page == 1:
                recs = [{"id": i, "title": f"m{i}"} for i in range(1, 1001)]   # full page (1000)
            else:
                recs = [{"id": 1001, "title": "m1001"}]                        # remainder
            return httpx.Response(200, json={"records": recs, "totalRecords": 1001})

        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        items = await client.list_missing()
        assert seen_pages == [1, 2]                       # walked both pages
        assert len(items) == 1001
        assert items[-1].remote_id == 1001

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

    async def test_list_queue_parses_download_id_and_size_left(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"records": [
                {"id": 5, "movieId": 11, "title": "A", "status": "downloading",
                 "downloadId": "ABC123", "sizeleft": 42, "added": "2026-06-15T00:00:00Z"},
                {"id": 6, "movieId": 12, "title": "B", "status": "downloadClientUnavailable",
                 "downloadId": None, "sizeleft": None, "added": "2026-06-15T00:00:00Z"},
            ]})
        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        items = await client.list_queue()
        assert (items[0].download_id, items[0].size_left) == ("ABC123", 42)
        assert (items[1].download_id, items[1].size_left) == ("", 0)   # null -> "" / 0

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


class TestRadarrHistory:
    async def test_list_grabbed_since_maps_events_and_date_param(self):
        seen = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["path"] = request.url.path
            seen["params"] = dict(request.url.params)
            return httpx.Response(200, json=[
                {"movieId": 366, "date": "2026-06-20T23:00:13Z",
                 "data": {"indexer": "BitSearch (Prowlarr)", "releaseSource": "Search"}},
                {"movieId": 331, "date": "2026-06-21T01:00:00Z",
                 "data": {"indexer": "The Pirate Bay (Prowlarr)", "releaseSource": "UserInvokedSearch"}},
            ])

        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        since = datetime(2026, 6, 20, 0, 0, tzinfo=timezone.utc)
        events = await client.list_grabbed_since(since)
        assert seen["path"] == "/api/v3/history/since"
        assert seen["params"]["eventType"] == "grabbed"
        assert seen["params"]["date"] == "2026-06-20T00:00:00Z"
        assert [(e.remote_id, e.indexer, e.release_source) for e in events] == [
            (366, "BitSearch (Prowlarr)", "Search"),
            (331, "The Pirate Bay (Prowlarr)", "UserInvokedSearch"),
        ]
        assert events[0].at == datetime(2026, 6, 20, 23, 0, 13, tzinfo=timezone.utc)

    async def test_list_grabbed_since_skips_rows_missing_id_or_date(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[
                {"movieId": 1, "date": "2026-06-21T01:00:00Z", "data": {"indexer": "X"}},
                {"date": "2026-06-21T01:00:00Z", "data": {"indexer": "Y"}},   # no id -> skip
                {"movieId": 2, "data": {"indexer": "Z"}},                     # no date -> skip
            ])

        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        events = await client.list_grabbed_since(datetime(2026, 6, 20, tzinfo=timezone.utc))
        assert [e.remote_id for e in events] == [1]


class TestSonarrHistory:
    async def test_list_grabbed_since_uses_episode_id(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=[
                {"episodeId": 8328, "date": "2026-06-21T01:00:00Z",
                 "data": {"indexer": "EZTVL (Prowlarr)", "releaseSource": "UserInvokedSearch"}}])

        client = SonarrClient(name="sonarr", base_url="http://sonarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="sk")
        events = await client.list_grabbed_since(datetime(2026, 6, 20, tzinfo=timezone.utc))
        assert events[0].remote_id == 8328 and events[0].indexer == "EZTVL (Prowlarr)"


    def test_sonarr_arr_type(self):
        from warden.models import ArrType
        client = SonarrClient(name="sonarr", base_url="http://sonarr",
                              http=httpx.AsyncClient(transport=transport(lambda r: httpx.Response(200, json={}))),
                              api_key="sk")
        assert client.arr_type == ArrType.SONARR


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


class TestWantedLastSearchTime:
    async def test_parses_last_search_time(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"records": [
                {"id": 11, "title": "A", "lastSearchTime": "2026-06-18T03:00:00Z"},
                {"id": 12, "title": "B"},                       # absent -> None
                {"id": 13, "title": "C", "lastSearchTime": None},  # null -> None
            ]})
        client = RadarrClient(name="radarr", base_url="http://radarr",
                              http=httpx.AsyncClient(transport=transport(handler)), api_key="rk")
        items = await client.list_missing()
        assert items[0].last_search_time == datetime(2026, 6, 18, 3, 0, tzinfo=timezone.utc)
        assert items[1].last_search_time is None
        assert items[2].last_search_time is None
