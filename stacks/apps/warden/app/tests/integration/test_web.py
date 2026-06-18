from fastapi.testclient import TestClient

from warden.container import Container
from warden.main import create_app


def make_client(monkeypatch) -> TestClient:
    # No *arr env -> zero instances; the web endpoints don't depend on hunting.
    for var in ("WARDEN_RADARR_URL", "WARDEN_RADARR_API_KEY", "WARDEN_SONARR_URL", "WARDEN_SONARR_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("WARDEN_DB_URL", "sqlite://")
    container = Container()
    return TestClient(create_app(container))


class TestWeb:
    def test_healthz_ok(self, monkeypatch):
        client = make_client(monkeypatch)
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_metrics_exposes_prometheus(self, monkeypatch):
        client = make_client(monkeypatch)
        resp = client.get("/metrics")
        assert resp.status_code == 200
        assert "warden_daily_budget" in resp.text
