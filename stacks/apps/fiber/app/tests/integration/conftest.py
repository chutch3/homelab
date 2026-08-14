from __future__ import annotations

from pathlib import Path

import pytest
from prometheus_client import CollectorRegistry

from fiber.clients.bowl import BowlStorage
from fiber.clients.dump_runner import DumpRunner
from fiber.clients.events import EventBroker
from fiber.clients.secrets import SecretReader
from fiber.clients.swarm import DockerSwarmGateway
from fiber.db.database import Database
from fiber.platform.clock import SystemClock
from fiber.platform.metrics import Metrics
from fiber.repositories.history import HistoryRepository
from fiber.services.orchestrator import MovementOrchestrator


def make_orchestrator(tmp_path: Path) -> MovementOrchestrator:
    """A real orchestrator wired to on-disk sqlite + a bowl under tmp_path.

    Shared by the postgres and mysql movement tests, which drive it against a
    real database container.
    """
    db = Database(url=f"sqlite:///{tmp_path}/fiber.db")
    return MovementOrchestrator(
        bowl_factory=lambda root: BowlStorage(root=root),
        bowl_root=str(tmp_path / "bowl"),
        secrets=SecretReader(base_dir=str(tmp_path / "secrets")),
        runner=DumpRunner(),
        history=HistoryRepository(session_factory=db.session),
        discovery=DockerSwarmGateway(client_factory=lambda: None),
        clock=SystemClock(),
        fiber_version="0.1.0",
        metrics=Metrics(registry=CollectorRegistry()),
        events=EventBroker(),
    )


def pytest_collection_finish(session: pytest.Session) -> None:
    """Disable coverage fail-under when only integration tests are collected (no unit tests)."""
    has_unit = any("tests/unit" in str(item.fspath) for item in session.items)
    if not has_unit:
        # Find the pytest-cov plugin and clear its fail-under threshold
        for name, plugin in session.config.pluginmanager.list_name_plugin():
            if hasattr(plugin, "options") and hasattr(plugin.options, "cov_fail_under"):
                plugin.options.cov_fail_under = None
                break
