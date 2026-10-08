"""In production the backend also serves the built frontend, so one service answers both the
pages and the API."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from disktracker.web import create_app


@pytest.fixture
def site(tmp_path: Path) -> Path:
    built = tmp_path / "dist"
    (built / "assets").mkdir(parents=True)
    (built / "index.html").write_text("<!doctype html><title>disktracker</title>")
    (built / "assets" / "app.js").write_text("console.log('app')")
    (tmp_path / "outside.txt").write_text("not part of the site")
    return built


def test_the_built_frontend_is_served_beside_the_api(database_url: str, site: Path) -> None:
    with TestClient(create_app(database_url, static_dir=str(site))) as client:
        home = client.get("/")
        script = client.get("/assets/app.js")
        # The Admin page is a route inside the app: the page is the same, the app shows it.
        admin = client.get("/admin")
        api = client.get("/api/sources")
        unknown_api = client.get("/api/nowhere")
        missing_file = client.get("/assets/missing.js")
        outside = client.get("/%2e%2e/outside.txt")

    assert (home.status_code, home.text) == (200, "<!doctype html><title>disktracker</title>")
    assert home.headers["content-type"].startswith("text/html")
    assert (script.status_code, script.text) == (200, "console.log('app')")
    assert (admin.status_code, admin.text) == (200, home.text)
    assert api.status_code == 200 and api.headers["content-type"] == "application/json"
    assert (unknown_api.status_code, unknown_api.json()) == (404, {"detail": "Not Found"})
    assert (missing_file.status_code, outside.status_code) == (404, 404)


def test_without_a_built_frontend_only_the_api_is_served(database_url: str) -> None:
    with TestClient(create_app(database_url)) as client:
        assert (client.get("/").status_code, client.get("/api/sources").status_code) == (404, 200)
