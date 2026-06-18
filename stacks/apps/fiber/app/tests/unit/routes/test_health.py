from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from unittest.mock import MagicMock

from fiber.config import Config
from fiber.container import Container
from fiber.main import create_app
from fiber.metrics import Metrics
from fiber.services.readiness import Readiness


class TestHealthRoutes:
    @pytest.fixture()
    def container(self) -> Container:
        c = Container()
        mock_config = MagicMock(spec=Config)
        mock_config.scan_enabled = False
        c.config.override(mock_config)
        return c

    @pytest.fixture()
    def app(self, container: Container):
        metrics = Metrics(registry=CollectorRegistry())
        readiness_mock = MagicMock(spec=Readiness)
        readiness_mock.return_value = True
        container.metrics.override(metrics)
        container.readiness.override(readiness_mock)
        yield create_app(container)
        container.metrics.reset_override()
        container.readiness.reset_override()

    def test_healthz_returns_200(self, app) -> None:
        with TestClient(app) as client:
            assert client.get("/healthz").status_code == 200

    def test_readyz_returns_200_when_ready(self, app) -> None:
        with TestClient(app) as client:
            assert client.get("/readyz").status_code == 200

    def test_readyz_returns_503_when_not_ready(self, app, container: Container) -> None:
        readiness_mock = MagicMock(spec=Readiness)
        readiness_mock.return_value = False
        container.readiness.override(readiness_mock)
        with TestClient(app) as client:
            assert client.get("/readyz").status_code == 503

    def test_metrics_endpoint_contains_fiber_metric(self, app) -> None:
        with TestClient(app) as client:
            body = client.get("/metrics").text
            assert "fiber_movements_total" in body

    def test_readyz_returns_503_not_500_when_readiness_raises(
        self, app, container: Container
    ) -> None:
        """If the readiness callable raises (e.g. Docker gateway error), /readyz must 503 not 500."""
        import docker
        readiness_mock = MagicMock(spec=Readiness)
        readiness_mock.side_effect = docker.errors.DockerException("gateway down")
        container.readiness.override(readiness_mock)
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/readyz")
        assert resp.status_code == 503

    def test_readyz_returns_503_not_500_when_docker_socket_absent(
        self, container: Container
    ) -> None:
        """End-to-end: container wired with a gateway whose factory raises → /readyz returns 503.

        This exercises the lazy-factory path: DI resolves swarm fine (no socket touched),
        Readiness.__call__ calls list_dump_services() which then raises, caught → False → 503.
        """
        import docker
        from fiber.clients.bowl import BowlStorage
        from fiber.clients.swarm import DockerSwarmGateway
        from fiber.repositories.history import HistoryRepository
        from unittest.mock import MagicMock

        def bad_factory() -> docker.DockerClient:
            raise docker.errors.DockerException("no docker socket")

        bad_swarm = DockerSwarmGateway(client_factory=bad_factory)
        bowl_mock = MagicMock(spec=BowlStorage)
        bowl_mock.has_room.return_value = True
        history_mock = MagicMock(spec=HistoryRepository)
        history_mock.last_success.return_value = None
        real_readiness = Readiness(bowl=bowl_mock, history=history_mock, swarm=bad_swarm)

        metrics = Metrics(registry=CollectorRegistry())
        container.metrics.override(metrics)
        container.readiness.override(real_readiness)
        app = create_app(container)

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/readyz")

        container.metrics.reset_override()
        container.readiness.reset_override()
        assert resp.status_code == 503
