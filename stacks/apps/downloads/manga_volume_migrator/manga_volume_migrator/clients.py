"""
manga_volume_migrator.clients

Abstractions over external HTTP services. These are the outer-ring seams —
mock these in tests, never the underlying HTTP library.
"""
from __future__ import annotations

import requests

from manga_volume_migrator.core import Chapter


class MangaDexClient:
    BASE_URL = "https://api.mangadex.org"

    def __init__(self, session: requests.Session | None = None) -> None:
        self._session = session or requests.Session()

    def fetch_aggregate(self, mangadex_uuid: str) -> dict:
        """Fetch the volume/chapter aggregate for a manga from MangaDex."""
        url = f"{self.BASE_URL}/manga/{mangadex_uuid}/aggregate"
        response = self._session.get(url, params={"translatedLanguage[]": "en"})
        response.raise_for_status()
        return response.json()


class TrangaClient:
    def __init__(self, base_url: str, session: requests.Session | None = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session or requests.Session()

    def get_chapters(self, manga_id: str) -> list[Chapter]:
        """Return all chapters for a manga from Tranga."""
        url = f"{self._base_url}/v2/Chapters/Manga/{manga_id}"
        chapters: list[Chapter] = []
        page = 1
        while True:
            response = self._session.post(url, params={"page": page, "pageSize": 100})
            response.raise_for_status()
            data = response.json()
            for item in data.get("items", []):
                chapters.append(Chapter(
                    key=item["key"],
                    chapter_number=item["chapterNumber"],
                    volume_number=item.get("volume"),
                    filename=item.get("fileName") or "",
                ))
            if page >= data.get("totalPages", 1):
                break
            page += 1
        return chapters

    def update_chapter(self, chapter_id: str, filename: str, volume_number: int | None) -> None:
        """Update FileName and VolumeNumber on a chapter via PATCH /v2/Chapters/{id}."""
        url = f"{self._base_url}/v2/Chapters/{chapter_id}"
        response = self._session.patch(url, json={
            "fileName": filename,
            "volumeNumber": volume_number,
        })
        response.raise_for_status()
