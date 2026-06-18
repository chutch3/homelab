from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.testclient import TestClient

from fiber.clients.events import EventBroker
from fiber.clients.probe import ConnectivityProbe, ProbeResult
from fiber.services.dashboard import DashboardService
from fiber.services.registry_state import RegistryState, Snapshot
from fiber.services.worker_pool import WorkerPool
from fiber.services.orchestrator import MovementOrchestrator
from fiber.status import DBStatus
from fiber.view import CardVM, Counts, DashboardVM, DiscoveryRow
from tests.factories import DumpJobFactory


def _make_card(service: str, status: DBStatus = DBStatus.CLEAN) -> CardVM:
    return CardVM(
        service=service,
        engine="postgres",
        status=status,
        last_rel="4h ago",
        size="100 MB",
        next_run="03:00",
        bristol=4,
        writes_to="/backups",
        error=None,
    )


def _make_vm(*services: str) -> DashboardVM:
    cards = [_make_card(s) for s in services]
    return DashboardVM(
        cards=cards,
        counts=Counts.from_cards(cards),
        discovery=[DiscoveryRow(service=s, result="discovered", detail="postgres") for s in services],
        bowl_path="/backups",
        bowl_used="16 GB",
        bowl_free="100 GB",
    )


class TestTilesToPush:
    """Unit tests for the pure tiles_to_push helper."""

    def _make_card(self, service: str, status: DBStatus) -> CardVM:
        return CardVM(
            service=service,
            engine="postgres",
            status=status,
            last_rel="1h ago",
            size="—",
            next_run="—",
            bristol=None,
            writes_to="/backups",
            error=None,
        )

    def test_returns_signalled_service_when_provided(self) -> None:
        from fiber.routes.dashboard import tiles_to_push
        cards = [
            self._make_card("immich", DBStatus.CLEAN),
            self._make_card("forgejo", DBStatus.STRAINING),
        ]
        assert tiles_to_push(cards, "immich") == ["immich"]

    def test_returns_straining_services_when_no_signal(self) -> None:
        from fiber.routes.dashboard import tiles_to_push
        cards = [
            self._make_card("immich", DBStatus.CLEAN),
            self._make_card("forgejo", DBStatus.STRAINING),
            self._make_card("paperless", DBStatus.STRAINING),
        ]
        result = tiles_to_push(cards, None)
        assert sorted(result) == ["forgejo", "paperless"]

    def test_returns_empty_when_no_signal_and_no_straining(self) -> None:
        from fiber.routes.dashboard import tiles_to_push
        cards = [
            self._make_card("immich", DBStatus.CLEAN),
            self._make_card("forgejo", DBStatus.CLOGGED),
        ]
        assert tiles_to_push(cards, None) == []

    def test_signalled_takes_priority_over_straining(self) -> None:
        from fiber.routes.dashboard import tiles_to_push
        cards = [
            self._make_card("immich", DBStatus.STRAINING),
            self._make_card("forgejo", DBStatus.STRAINING),
        ]
        # when signalled, only push the signalled service
        result = tiles_to_push(cards, "immich")
        assert result == ["immich"]


class TestDashboardRoutes:
    @pytest.fixture()
    def mock_dashboard_service(self) -> MagicMock:
        m = create_autospec(DashboardService, instance=True)
        m.build.return_value = _make_vm("immich", "forgejo")
        m.detail.return_value = _make_card("immich")
        m.card.return_value = _make_card("immich")
        return m

    @pytest.fixture()
    def mock_pool(self) -> MagicMock:
        m = create_autospec(WorkerPool, instance=True)
        m.submit.return_value = None
        m.cancel.return_value = True
        return m

    @pytest.fixture()
    def mock_broker(self) -> MagicMock:
        m = create_autospec(EventBroker, instance=True)
        m.subscribe.return_value = asyncio.Queue()
        return m

    @pytest.fixture()
    def mock_orchestrator(self) -> MagicMock:
        m = create_autospec(MovementOrchestrator, instance=True)
        m.perform = AsyncMock()
        return m

    @pytest.fixture()
    def mock_registry_state(self) -> MagicMock:
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *")
        m = create_autospec(RegistryState, instance=True)
        snap = Snapshot(jobs=[job], misconfigured=[], skipped=[])
        m.get.return_value = snap
        return m

    @pytest.fixture()
    def mock_probe(self) -> MagicMock:
        m = create_autospec(ConnectivityProbe, instance=True)
        m.check = AsyncMock(return_value=ProbeResult(ok=True, detail="accepting connections"))
        return m

    @pytest.fixture()
    def templates(self, tmp_path) -> Jinja2Templates:
        # Minimal templates for unit tests
        tmpl_dir = tmp_path / "templates"
        tmpl_dir.mkdir()
        (tmpl_dir / "wall.html").write_text(
            "<html><body>{% for c in vm.cards %}<div id='tile-{{ c.service }}'>{{ c.service }}</div>{% endfor %}</body></html>"
        )
        (tmpl_dir / "_tile.html").write_text(
            "<div id='tile-{{ c.service }}' class='s-{{ c.status.value }}'>{{ c.service }}</div>"
        )
        (tmpl_dir / "_drawer.html").write_text(
            "<div class='drawer-content'>{{ d.service }}</div>"
        )
        (tmpl_dir / "_summary.html").write_text(
            "<div id='summary'>{% if vm.verdict_ok %}ALL REGULAR{% else %}{{ vm.needs_attention }} NEED ATTENTION{% endif %}</div>"
        )
        (tmpl_dir / "_discovery.html").write_text(
            "{% for r in rows %}<tr><td>{{ r.service }}</td><td>{{ r.result }}</td></tr>{% endfor %}"
        )
        (tmpl_dir / "_probe_result.html").write_text(
            "{% if ok %}<span class='probe-ok'>✓ reachable</span>{% else %}<span class='probe-fail'>✕ {{ detail }}</span>{% endif %}"
        )
        return Jinja2Templates(directory=str(tmpl_dir))

    @pytest.fixture()
    def app(
        self,
        mock_dashboard_service: MagicMock,
        mock_pool: MagicMock,
        mock_broker: MagicMock,
        mock_orchestrator: MagicMock,
        mock_registry_state: MagicMock,
        mock_probe: MagicMock,
        templates: Jinja2Templates,
    ) -> FastAPI:
        from fiber.config import Config
        from fiber.container import Container
        from fiber.main import create_app

        container = Container()
        mock_config = MagicMock(spec=Config)
        mock_config.scan_enabled = False
        container.config.override(mock_config)
        container.dashboard_service.override(mock_dashboard_service)
        container.pool.override(mock_pool)
        container.events.override(mock_broker)
        container.orchestrator.override(mock_orchestrator)
        container.registry_state.override(mock_registry_state)
        container.probe.override(mock_probe)
        container.templates.override(templates)
        app = create_app(container)
        return app

    def test_get_root_returns_200(self, app: FastAPI) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        assert resp.status_code == 200

    def test_get_root_contains_service_names(self, app: FastAPI) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        assert "immich" in resp.text
        assert "forgejo" in resp.text

    def test_get_root_contains_tile_ids(self, app: FastAPI) -> None:
        with TestClient(app) as client:
            resp = client.get("/")
        assert "tile-immich" in resp.text
        assert "tile-forgejo" in resp.text

    def test_post_flush_calls_pool_submit(
        self, app: FastAPI, mock_pool: MagicMock
    ) -> None:
        with TestClient(app) as client:
            resp = client.post("/db/immich/flush")
        assert resp.status_code == 200
        mock_pool.submit.assert_called_once()
        call_args = mock_pool.submit.call_args
        assert call_args[0][0] == "immich"

    def test_post_pinch_calls_pool_cancel(
        self, app: FastAPI, mock_pool: MagicMock
    ) -> None:
        with TestClient(app) as client:
            resp = client.post("/db/immich/pinch")
        assert resp.status_code == 200
        mock_pool.cancel.assert_called_once_with("immich")

    def test_get_drawer_returns_partial(self, app: FastAPI) -> None:
        with TestClient(app) as client:
            resp = client.get("/db/immich")
        assert resp.status_code == 200
        assert "immich" in resp.text

    def test_get_discovery_returns_rows(self, app: FastAPI) -> None:
        with TestClient(app) as client:
            resp = client.get("/discovery")
        assert resp.status_code == 200

    def test_post_flush_all_calls_pool_submit_for_each(
        self, app: FastAPI, mock_pool: MagicMock
    ) -> None:
        with TestClient(app) as client:
            resp = client.post("/flush-all")
        assert resp.status_code == 200

    def test_post_test_connection_calls_probe_and_returns_partial(
        self, app: FastAPI, mock_probe: MagicMock
    ) -> None:
        with TestClient(app) as client:
            resp = client.post("/db/immich/test")
        assert resp.status_code == 200
        mock_probe.check.assert_called_once()
        assert "reachable" in resp.text

    def test_post_test_connection_not_ok_shows_detail(
        self, app: FastAPI, mock_probe: MagicMock
    ) -> None:
        mock_probe.check = AsyncMock(
            return_value=ProbeResult(ok=False, detail="no response")
        )
        with TestClient(app) as client:
            resp = client.post("/db/immich/test")
        assert resp.status_code == 200
        assert "no response" in resp.text
