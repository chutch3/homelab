from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from prometheus_client import CollectorRegistry

from fiber.platform.config import Config
from fiber.container import Container
from fiber.main import create_app
from fiber.platform.metrics import Metrics
from fiber.services.registry_state import RegistryState


def _make_container(scan_enabled: bool = True) -> Container:
    """Build a minimal wired container with mocked infrastructure."""
    c = Container()
    mock_config = MagicMock(spec=Config)
    mock_config.scan_enabled = scan_enabled
    mock_config.scan_interval = 0.0
    mock_config.bowl_path = "/tmp/test-bowl"
    mock_config.max_concurrent = 1
    c.config.override(mock_config)
    c.metrics.override(Metrics(registry=CollectorRegistry()))
    rs = RegistryState()
    c.registry_state.override(rs)
    return c


class TestCreateApp:
    def test_create_app_returns_fastapi_app(self) -> None:
        from fastapi import FastAPI
        c = _make_container(scan_enabled=False)
        app = create_app(c)
        assert isinstance(app, FastAPI)

    def test_create_app_with_no_container_arg_uses_default(self) -> None:
        """create_app() with no arg must not raise (Container() constructed internally)."""
        # We can't fully wire without real env, so just test the signature accepts None
        import inspect
        sig = inspect.signature(create_app)
        params = list(sig.parameters.values())
        assert len(params) == 1
        assert params[0].name == "container"
        assert params[0].default is None

    def test_healthz_returns_200(self) -> None:
        c = _make_container(scan_enabled=False)
        app = create_app(c)
        with TestClient(app) as client:
            resp = client.get("/healthz")
        assert resp.status_code == 200

    def test_static_mount_present(self) -> None:
        c = _make_container(scan_enabled=False)
        app = create_app(c)
        route_paths = [getattr(r, "path", str(r)) for r in app.routes]
        assert any("/static" in p for p in route_paths)


class TestLifespanScanLoop:
    def test_scan_loop_not_started_when_scan_disabled(self) -> None:
        """With scan_enabled=False, _scan_loop must never be called during lifespan."""
        c = _make_container(scan_enabled=False)
        app = create_app(c)

        with patch("fiber.main._scan_loop", new_callable=AsyncMock) as mock_loop:
            with TestClient(app):
                pass  # startup + shutdown triggered by context manager

        mock_loop.assert_not_called()

    def test_scan_loop_started_when_scan_enabled(self) -> None:
        """With scan_enabled=True, _scan_loop must be created as an asyncio task on startup."""
        c = _make_container(scan_enabled=True)
        app = create_app(c)

        loop_started = False

        async def _fake_loop(stop: asyncio.Event) -> None:
            nonlocal loop_started
            loop_started = True
            await stop.wait()

        with patch("fiber.main._scan_loop", side_effect=_fake_loop):
            with TestClient(app):
                pass

        assert loop_started, "_scan_loop was not invoked during lifespan startup"

    def test_scan_loop_stop_event_set_on_shutdown(self) -> None:
        """On lifespan shutdown the stop event must be set, causing _scan_loop to exit."""
        c = _make_container(scan_enabled=True)
        app = create_app(c)

        stop_events: list[asyncio.Event] = []

        async def _capture_stop(stop: asyncio.Event) -> None:
            stop_events.append(stop)
            await stop.wait()

        with patch("fiber.main._scan_loop", side_effect=_capture_stop):
            with TestClient(app):
                pass  # exit triggers shutdown

        assert len(stop_events) == 1
        assert stop_events[0].is_set(), "stop event was not set on shutdown"
