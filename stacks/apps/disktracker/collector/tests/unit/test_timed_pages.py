from typing import Any

import httpx
import pytest

from collector.errors import OutOfTime
from collector.polite import TimedPages
from tests.fakes import FakeClock


class FakePages:
    """A store that answers every page, and none of them is there."""

    def __init__(self) -> None:
        self.asked: list[str] = []

    def get(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response:
        self.asked.append(url)
        return httpx.Response(200, text="page")

    def get_if_present(
        self, url: str, params: dict[str, Any] | None = None, min_delay: float = 0
    ) -> httpx.Response | None:
        self.asked.append(url)
        return None

    def sitemaps(self, url: str) -> list[str]:
        return [f"{url}/sitemap.xml"]

    def crawl_delay(self, url: str) -> float:
        return 20.0


def test_pages_are_fetched_until_the_time_is_up_and_then_it_says_how_far_it_got() -> None:
    clock, store = FakeClock(), FakePages()
    pages = TimedPages(store, clock, seconds=30)

    assert pages.get("https://store.test/a").text == "page"
    clock.advance(30)
    assert pages.get_if_present("https://store.test/b") is None
    assert pages.sitemaps("https://store.test") == ["https://store.test/sitemap.xml"]
    assert pages.crawl_delay("https://store.test") == 20.0
    clock.advance(1)
    with pytest.raises(OutOfTime, match="out of time after 30 seconds: 2 requests made, the last"):
        pages.get("https://store.test/c")
    with pytest.raises(OutOfTime, match="the last for https://store.test/b"):
        pages.get_if_present("https://store.test/d")
    assert store.asked == ["https://store.test/a", "https://store.test/b"]
