"""Fetching pages through FlareSolverr, a headless browser, for stores that answer only
browsers. It stands in for httpx.Client under PoliteHttp, so robots.txt (read through the
browser too) and request spacing still apply. The browser sends its own headers: the collector
cannot identify itself to a store read this way, which is why a source's basis matters."""

import html
import re
from typing import Any

import httpx

from collector.errors import SourceUnavailable

# FlareSolverr gives up on a page after this long; the request to it waits a little longer.
MAX_TIMEOUT_MS = 60_000
# How Chrome shows a JSON (or plain text) document: its text in a <pre>, in a page whose head
# holds only Chrome's own color-scheme and charset tags.
RENDERED_TEXT = re.compile(
    r'^\s*<html><head><meta name="color-scheme" content="light dark">(?:<meta charset="[^"]*">)?'
    r"</head><body><pre[^>]*>(.*?)</pre>",
    re.DOTALL,
)


class BrowserFailed(httpx.HTTPError):
    """FlareSolverr could not get the page."""


def page_text(rendered: str) -> str:
    """The document as the store sent it, where the browser rendered it as text."""
    match = RENDERED_TEXT.match(rendered)
    return html.unescape(match[1]) if match else rendered


class BrowserHttp:
    def __init__(
        self, http: httpx.Client, flaresolverr_url: str | None, proxy_url: str | None = None
    ) -> None:
        """flaresolverr_url: None when there is no FlareSolverr to use; nothing can then be
        fetched through a browser. proxy_url: the proxy the browser is told to fetch each page
        through, as the collector's own fetches go; FlareSolverr itself is asked directly."""
        self.http = http
        self.through = {"proxy": {"url": proxy_url}} if proxy_url else {}
        self.endpoint = f"{flaresolverr_url.rstrip('/')}/v1" if flaresolverr_url else None

    def get(self, url: str, *, headers: dict[str, str]) -> httpx.Response:
        """The page at url as the browser got it: its status and its text. The headers are the
        collector's own, which the browser does not send."""
        if self.endpoint is None:
            raise SourceUnavailable("settings: fetching through a browser needs FLARESOLVERR_URL")
        answer = self.http.post(
            self.endpoint,
            json={"cmd": "request.get", "url": url, "maxTimeout": MAX_TIMEOUT_MS, **self.through},
        )
        try:
            body: dict[str, Any] = answer.json()
        except ValueError as error:
            raise BrowserFailed(f"browser: HTTP {answer.status_code}") from error
        if body.get("status") != "ok":
            raise BrowserFailed(f"browser: {body.get('message') or answer.status_code}")
        solution = body["solution"]
        return httpx.Response(
            solution["status"],
            text=page_text(solution["response"]),
            request=httpx.Request("GET", url),
        )
