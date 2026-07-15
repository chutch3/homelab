from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry
from unittest.mock import MagicMock

from fiber.container import Container
from fiber.main import create_app
from fiber.platform.metrics import Metrics
from fiber.services.readiness import Readiness


@pytest.fixture()
def container():
    c = Container()
    metrics = Metrics(registry=CollectorRegistry())
    readiness_mock = MagicMock(spec=Readiness)
    readiness_mock.return_value = True
    c.metrics.override(metrics)
    c.readiness.override(readiness_mock)
    yield c
    c.metrics.reset_override()
    c.readiness.reset_override()


def test_health_and_metrics_endpoints(container: Container) -> None:
    app = create_app(container)
    client = TestClient(app)
    assert client.get("/healthz").status_code == 200
    assert client.get("/readyz").status_code == 200
    body = client.get("/metrics").text
    assert "fiber_movements_total" in body


def test_readyz_returns_503_when_not_ready(container: Container) -> None:
    readiness_mock = MagicMock(spec=Readiness)
    readiness_mock.return_value = False
    container.readiness.override(readiness_mock)
    app = create_app(container)
    client = TestClient(app)
    assert client.get("/readyz").status_code == 503
