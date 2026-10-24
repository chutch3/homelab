from collections.abc import Iterator

import pytest
from pytest_httpserver import HTTPServer

from tests.integration.harness import serve_runs


def fake_server() -> Iterator[HTTPServer]:
    server = HTTPServer()
    server.start()
    yield server
    server.clear()
    if server.is_running():
        server.stop()


@pytest.fixture
def disktracker() -> Iterator[HTTPServer]:
    """A fake disktracker that registers every run the collector starts, hears how far each has
    got without asking it to stop, takes its end, and hears every heartbeat."""
    for server in fake_server():
        serve_runs(server)
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
