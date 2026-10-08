import json

import httpx
import pytest
from pytest_httpserver import HTTPServer

from collector.browser import BrowserFailed, BrowserHttp, page_text
from collector.errors import SourceUnavailable


def test_a_document_the_browser_rendered_as_text_is_read_back_as_sent() -> None:
    rendered = (
        '<html><head><meta name="color-scheme" content="light dark"></head><body>'
        '<pre style="white-space: pre-wrap;">{"title": "A &amp; B &lt;18TB&gt;"}</pre>'
        '<div class="json-formatter-container"></div></body></html>'
    )
    assert json.loads(page_text(rendered)) == {"title": "A & B <18TB>"}


def test_an_html_page_is_left_as_it_is() -> None:
    page = "<html><head><title>Drive</title></head><body><pre>spec</pre></body></html>"
    assert page_text(page) == page


def test_an_answer_that_is_not_flaresolverrs_fails_with_its_status(httpserver: HTTPServer) -> None:
    httpserver.expect_request("/v1", method="POST").respond_with_data("bad gateway", status=502)
    with httpx.Client() as http, pytest.raises(BrowserFailed, match="^browser: HTTP 502$"):
        BrowserHttp(http, httpserver.url_for("/")).get("https://store.test/", headers={})


def test_without_a_flaresolverr_to_use_nothing_can_be_fetched_through_a_browser() -> None:
    with (
        httpx.Client() as http,
        pytest.raises(
            SourceUnavailable, match="^settings: fetching through a browser needs FLARESOLVERR_URL$"
        ),
    ):
        BrowserHttp(http, None).get("https://store.test/", headers={})
