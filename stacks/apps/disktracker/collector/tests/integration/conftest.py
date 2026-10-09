from collections.abc import Iterator

import pytest
from pytest_httpserver import HTTPServer
from werkzeug import Request, Response


def fake_server() -> Iterator[HTTPServer]:
    server = HTTPServer()
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


def echo(request: Request) -> Response:
    return Response(request.data, status=201, content_type="application/json")


@pytest.fixture
def disktracker() -> Iterator[HTTPServer]:
    """A fake disktracker that takes every run report the collector sends, and hears how far
    each run has got without asking it to stop."""
    for server in fake_server():
        server.expect_request("/api/collector-runs", method="POST").respond_with_handler(echo)
        server.expect_request("/api/collector-activity", method="PUT").respond_with_json(
            {"stop": False}
        )
        yield server


@pytest.fixture
def serverpartdeals() -> Iterator[HTTPServer]:
    yield from fake_server()


@pytest.fixture
def goharddrive() -> Iterator[HTTPServer]:
    yield from fake_server()


@pytest.fixture
def westerndigital() -> Iterator[HTTPServer]:
    yield from fake_server()


@pytest.fixture
def serverorbit() -> Iterator[HTTPServer]:
    yield from fake_server()


@pytest.fixture
def seagate() -> Iterator[HTTPServer]:
    yield from fake_server()


@pytest.fixture
def flaresolverr() -> Iterator[HTTPServer]:
    yield from fake_server()
