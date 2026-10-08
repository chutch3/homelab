import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import psycopg
import pytest

pytest_plugins = ["pytester"]


@pytest.fixture
def container_factory(monkeypatch: pytest.MonkeyPatch, db_fixture: ModuleType) -> MagicMock:
    factory = MagicMock()
    factory.return_value.__enter__.return_value.get_connection_url.return_value = (
        "postgresql://test:test@127.0.0.1:49152/test"
    )
    monkeypatch.setattr(db_fixture, "PostgresContainer", factory)
    return factory


@pytest.fixture(params=["backend", "e2e"])
def db_fixture(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root = Path(__file__).parents[3]
    directory = root / "backend/tests" if request.param == "backend" else root / "tests/e2e"
    spec = importlib.util.spec_from_file_location("database_fixture_under_test", directory / "conftest.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, spec.name, module)
    return module


def test_explicit_server_bypasses_testcontainers(
    monkeypatch: pytest.MonkeyPatch, container_factory: MagicMock, db_fixture: ModuleType
) -> None:
    url = "postgresql://test:test@localhost:55432/postgres"
    monkeypatch.setenv("DISKTRACKER_TEST_ADMIN_URL", f" {url} ")

    assert list(db_fixture.database_admin_url.__wrapped__()) == [url]
    container_factory.assert_not_called()


@pytest.mark.parametrize("override", [None, "", " \t "])
def test_missing_or_blank_override_owns_a_container(
    override: str | None,
    monkeypatch: pytest.MonkeyPatch,
    container_factory: MagicMock,
    db_fixture: ModuleType,
) -> None:
    monkeypatch.delenv("DISKTRACKER_TEST_ADMIN_URL", raising=False)
    if override is not None:
        monkeypatch.setenv("DISKTRACKER_TEST_ADMIN_URL", override)
    fixture = db_fixture.database_admin_url.__wrapped__()

    assert next(fixture) == "postgresql://test:test@127.0.0.1:49152/test"
    container_factory.assert_called_once_with("postgres:16-alpine", driver=None)
    container_factory.return_value.__exit__.assert_not_called()
    fixture.close()
    container_factory.return_value.__exit__.assert_called_once()


def test_bad_explicit_connection_does_not_fall_back_to_docker(
    monkeypatch: pytest.MonkeyPatch, container_factory: MagicMock, db_fixture: ModuleType
) -> None:
    monkeypatch.setenv("DISKTRACKER_TEST_ADMIN_URL", "postgresql://unavailable/postgres")
    connection = MagicMock(side_effect=psycopg.OperationalError("test server unavailable"))
    monkeypatch.setattr(db_fixture.psycopg, "connect", connection)
    admin_fixture = db_fixture.database_admin_url.__wrapped__()

    with pytest.raises(psycopg.OperationalError, match="test server unavailable"):
        next(db_fixture.database_url.__wrapped__(next(admin_fixture)))

    admin_fixture.close()
    container_factory.assert_not_called()


def test_tests_without_database_fixtures_do_not_start_a_container(
    monkeypatch: pytest.MonkeyPatch, container_factory: MagicMock, pytester: pytest.Pytester
) -> None:
    monkeypatch.delenv("DISKTRACKER_TEST_ADMIN_URL", raising=False)
    pytester.makeconftest("from database_fixture_under_test import database_admin_url, database_url")
    pytester.makepyfile("def test_without_database(): assert True")

    result = pytester.runpytest("-q", "-o", "addopts=")

    result.assert_outcomes(passed=1)
    container_factory.assert_not_called()


def test_one_container_per_session_and_cleanup_after_a_failed_test(
    monkeypatch: pytest.MonkeyPatch, container_factory: MagicMock, pytester: pytest.Pytester
) -> None:
    monkeypatch.delenv("DISKTRACKER_TEST_ADMIN_URL", raising=False)
    pytester.makeconftest("from database_fixture_under_test import database_admin_url")
    pytester.makepyfile(
        """
        def test_first(database_admin_url):
            assert database_admin_url == 'postgresql://test:test@127.0.0.1:49152/test'

        def test_second(database_admin_url):
            assert False, 'intentional failure to exercise cleanup'
        """
    )

    result = pytester.runpytest("-q", "-o", "addopts=")

    result.assert_outcomes(passed=1, failed=1)
    container_factory.assert_called_once_with("postgres:16-alpine", driver=None)
    container_factory.return_value.__exit__.assert_called_once()
