import pytest
from unittest.mock import MagicMock

from manga_volume_migrator import migrate
from manga_volume_migrator.clients import MangaDexClient, TrangaClient
from manga_volume_migrator.core import Chapter

AGGREGATE_RESPONSE = {
    "result": "ok",
    "volumes": {
        "1": {
            "volume": "1",
            "chapters": {
                "1": {"chapter": "1", "id": "abc", "others": [], "count": 1},
                "2": {"chapter": "2", "id": "def", "others": [], "count": 1},
            },
        },
    },
}


class TestMigrate:
    @pytest.fixture
    def mangadex_client(self):
        client = MagicMock(spec=MangaDexClient)
        client.fetch_aggregate.return_value = AGGREGATE_RESPONSE
        return client

    @pytest.fixture
    def tranga_client(self):
        client = MagicMock(spec=TrangaClient)
        client.get_chapters.return_value = [
            Chapter("Chapter-1", "1", None, "Berserk - Ch.1.cbz"),
            Chapter("Chapter-2", "2", None, "Berserk - Ch.2.cbz"),
        ]
        return client

    @pytest.fixture
    def subject(self, mangadex_client, tranga_client):
        def run(**kwargs):
            return migrate(
                manga_name="Berserk",
                manga_id="Manga-abc",
                mangadex_uuid="uuid-123",
                mangadex_client=mangadex_client,
                tranga_client=tranga_client,
                **kwargs,
            )
        return run

    def test_fetches_aggregate_with_provided_mangadex_uuid(self, subject, mangadex_client):
        subject()
        mangadex_client.fetch_aggregate.assert_called_once_with("uuid-123")

    def test_queries_chapters_with_provided_manga_id(self, subject, tranga_client):
        subject()
        tranga_client.get_chapters.assert_called_once_with("Manga-abc")

    def test_updates_tranga_for_each_chapter_needing_a_move(self, subject, tranga_client):
        subject()
        tranga_client.update_chapter.assert_any_call(
            "Chapter-1", "Berserk Vol 1/Berserk - Ch.1.cbz", 1
        )
        tranga_client.update_chapter.assert_any_call(
            "Chapter-2", "Berserk Vol 1/Berserk - Ch.2.cbz", 1
        )

    def test_returns_zero_when_all_succeed(self, subject):
        assert subject() == 0

    def test_dry_run_skips_update(self, subject, tranga_client):
        subject(dry_run=True)
        tranga_client.update_chapter.assert_not_called()

    def test_returns_error_count_when_update_fails(self, subject, tranga_client):
        tranga_client.update_chapter.side_effect = Exception("connection refused")
        errors = subject()
        assert errors == 2

    def test_continues_updating_remaining_chapters_after_one_fails(self, subject, tranga_client):
        tranga_client.update_chapter.side_effect = [Exception("timeout"), None]
        errors = subject()
        assert errors == 1
        assert tranga_client.update_chapter.call_count == 2
