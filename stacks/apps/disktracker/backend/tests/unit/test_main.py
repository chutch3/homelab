import pytest

from disktracker.container import Container
from disktracker.main import create_app

DATABASE = "postgresql+psycopg://unused@localhost/unused"


def test_the_application_is_configured_from_the_environment_into_the_container_given(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Nothing connects until a request is served, so the address need not answer.
    monkeypatch.setenv("DISKTRACKER_DATABASE_URL", DATABASE)
    monkeypatch.setenv("DISKTRACKER_COLLECTOR_URL", "http://collector.test:8100")
    monkeypatch.delenv("DISKTRACKER_STATIC_DIR", raising=False)
    container = Container()

    app = create_app(container)

    assert container.config() == {
        "database_url": DATABASE,
        "collector_url": "http://collector.test:8100",
        "static_dir": None,
    }
    assert {"/api/offers", "/api/sources", "/api/trends"} <= set(app.openapi()["paths"])


def test_without_a_database_the_application_is_not_made(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DISKTRACKER_DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DISKTRACKER_DATABASE_URL"):
        create_app()
