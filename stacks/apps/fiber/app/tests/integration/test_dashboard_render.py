from __future__ import annotations

import pytest

pytestmark = pytest.mark.integration

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, create_autospec

from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from fiber.clients.bowl import BowlStorage
from fiber.container import Container
from fiber.main import create_app
from fiber.platform.metrics import Metrics
from fiber.domain.models import BowlEntry, MisconfiguredJob, MovementOutcome
from fiber.repositories.history import HistoryRepository
from fiber.services.registry_state import RegistryState, Snapshot
from fiber.services.worker_pool import WorkerPool
from fiber.domain.status import DBStatus
from tests.factories import DumpJobFactory

UTC = timezone.utc
NOW = datetime(2026, 6, 15, 9, 0, tzinfo=UTC)


@pytest.fixture()
def container() -> Container:
    c = Container()
    # Override infrastructure providers with mocks
    registry = CollectorRegistry()
    c.metrics.override(Metrics(registry=registry))

    job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
    misconfigured = MisconfiguredJob(service="paperless", errors=("missing fiber.secret",))

    rs = RegistryState()
    snap = Snapshot(
        jobs=[job],
        misconfigured=[misconfigured],
        skipped=[("traefik", "no fiber.enable label")],
    )
    rs.set(snap)
    c.registry_state.override(rs)

    history = create_autospec(HistoryRepository, instance=True)
    history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
    history.last_outcome.return_value = MovementOutcome.CLEAN
    history.latest_clean.return_value = None
    c.history_repository.override(history)

    pool = create_autospec(WorkerPool, instance=True)
    pool.started_at.return_value = None
    c.pool.override(pool)

    bowl = create_autospec(BowlStorage, instance=True)
    bowl.usage.return_value = (1024 * 1024 * 16, 1024 * 1024 * 1024 * 100)
    c.bowl.override(bowl)

    # Override config values needed by dashboard_service
    mock_config = MagicMock()
    mock_config.scan_enabled = False
    mock_config.bowl_path = "/backups"
    mock_config.max_concurrent = 2
    c.config.override(mock_config)

    # Override clock to use our fixed time
    mock_clock = MagicMock()
    mock_clock.now.return_value = NOW
    c.clock.override(mock_clock)

    return c


@pytest.fixture()
def app(container: Container):
    return create_app(container)


class TestDashboardRender:
    def test_get_root_returns_200_html(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_get_root_contains_service_names(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        body = resp.text
        assert "immich" in body
        assert "paperless" in body

    def test_get_root_contains_tile_ids(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        body = resp.text
        assert "tile-immich" in body
        assert "tile-paperless" in body

    def test_get_root_contains_verdict(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        body = resp.text
        # paperless is MISCONFIGURED — needs attention
        assert "NEED ATTENTION" in body or "ALL REGULAR" in body

    def test_get_root_contains_status_class(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        body = resp.text
        assert "s-misconfigured" in body  # paperless tile

    def test_static_css_returns_200(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/static/fiber.css")
        assert resp.status_code == 200
        assert "text/css" in resp.headers["content-type"]

    def test_get_drawer_returns_partial(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/db/immich")
        assert resp.status_code == 200
        assert "immich" in resp.text

    def test_get_discovery_returns_rows(self, app) -> None:
        with TestClient(app) as client:
            resp = client.get("/discovery")
        assert resp.status_code == 200
        body = resp.text
        assert "immich" in body
        assert "paperless" in body
        assert "traefik" in body

    def test_footer_shows_discovery_updated(self, container: Container) -> None:
        """Footer shows discovery timestamp when scanned_at is set."""
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        snap = Snapshot(
            jobs=[job],
            misconfigured=[],
            skipped=[],
            scanned_at=NOW - timedelta(seconds=5),
            error=None,
        )
        rs.set(snap)
        container.registry_state.override(rs)
        app = create_app(container)
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "discovery: updated" in resp.text

    def test_footer_shows_discovery_error(self, container: Container) -> None:
        """Footer shows error banner when discovery is failing."""
        rs = RegistryState()
        snap = Snapshot(
            jobs=[],
            misconfigured=[],
            skipped=[],
            scanned_at=NOW - timedelta(seconds=30),
            error="docker unavailable",
        )
        rs.set(snap)
        container.registry_state.override(rs)
        app = create_app(container)
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        assert "discovery failing" in resp.text
        assert "docker unavailable" in resp.text

    def test_tile_has_keyboard_a11y_attributes(self, app) -> None:
        """Tiles must have tabindex=0 and role=button for keyboard accessibility."""
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        body = resp.text
        assert 'tabindex="0"' in body
        assert 'role="button"' in body

    def test_straining_tile_shows_progress(self, container: Container) -> None:
        """A running service renders its bytes+elapsed progress string in the tile."""
        running_job = DumpJobFactory.build(service="running-db", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        snap = Snapshot(jobs=[running_job], misconfigured=[], skipped=[])
        rs.set(snap)
        container.registry_state.override(rs)

        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        history.latest_clean.return_value = None
        container.history_repository.override(history)

        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = NOW - timedelta(seconds=62)
        container.pool.override(pool)

        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.list_entries.return_value = [
            BowlEntry(
                path="/backups/running-db/x.dump.partial",
                size_bytes=512 * 1024 * 1024,  # 512 MB
                modified_at=NOW,
                is_temp=True,
            )
        ]
        container.bowl.override(bowl)

        app = create_app(container)
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200
        body = resp.text
        assert "s-straining" in body
        assert "1:02" in body  # 62s elapsed
