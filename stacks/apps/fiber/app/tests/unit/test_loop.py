from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, create_autospec

import pytest
from prometheus_client import CollectorRegistry

from fiber.clock import SystemClock
from fiber.repositories.history import HistoryRepository
from fiber.metrics import Metrics
from fiber.clients.swarm import DockerSwarmGateway
from fiber.services.registry_state import RegistryState
from fiber.services.worker_pool import WorkerPool
from tests.factories import DumpJobFactory


def _base_mocks() -> tuple[MagicMock, MagicMock, MagicMock, MagicMock, Metrics, asyncio.Event, RegistryState]:
    swarm = MagicMock(spec=DockerSwarmGateway)
    swarm.list_dump_services.return_value = {
        "kenku-pg": {
            "fiber.enable": "true",
            "fiber.schedule": "0 3 * * *",
            "fiber.host": "kenku-pg",
            "fiber.port": "5432",
            "fiber.user": "k",
            "fiber.dbname": "k",
            "fiber.secret": "s",
        }
    }
    history = MagicMock(spec=HistoryRepository)
    history.last_success.return_value = None
    history.median_bytes.return_value = None

    pool = MagicMock(spec=WorkerPool)
    pool.running_services.return_value = set()

    clock = create_autospec(SystemClock, instance=True)
    clock.now.return_value = datetime(2026, 6, 16, 4, tzinfo=timezone.utc)

    metrics = Metrics(registry=CollectorRegistry())

    stop = asyncio.Event()
    stop.set()  # run exactly one iteration

    registry_state = RegistryState()

    return swarm, history, pool, clock, metrics, stop, registry_state


async def test_skipped_overlap_incremented_when_pool_returns_none() -> None:
    """When pool.submit returns None (already running), skipped_overlap counter must be incremented."""
    swarm, history, pool, clock, metrics, stop, registry_state = _base_mocks()
    pool.submit.return_value = None  # signals overlap
    orchestrator = AsyncMock()

    from fiber.loop import _scan_loop_inner
    await _scan_loop_inner(
        swarm=swarm,
        history=history,
        pool=pool,
        orchestrator=orchestrator,
        clock=clock,
        metrics=metrics,
        stop=stop,
        interval=0,
        registry_state=registry_state,
    )

    count = metrics.registry.get_sample_value("fiber_skipped_overlap_total", {"db": "kenku-pg"})
    assert count == 1.0, f"expected skipped_overlap=1 for kenku-pg, got {count}"


async def test_job_enqueued_when_pool_submit_returns_task() -> None:
    """When pool.submit returns a task (not None), the job is enqueued (else branch covered)."""
    swarm, history, pool, clock, metrics, stop, registry_state = _base_mocks()
    pool.submit.return_value = asyncio.create_task(asyncio.sleep(0))  # non-None task
    orchestrator = AsyncMock()

    from fiber.loop import _scan_loop_inner
    await _scan_loop_inner(
        swarm=swarm,
        history=history,
        pool=pool,
        orchestrator=orchestrator,
        clock=clock,
        metrics=metrics,
        stop=stop,
        interval=0,
        registry_state=registry_state,
    )

    pool.submit.assert_called_once()


async def test_misconfigured_service_logs_warning() -> None:
    """Misconfigured services (missing required labels) are logged as warnings."""
    swarm = MagicMock(spec=DockerSwarmGateway)
    # Service opted in but missing required labels — will be misconfigured
    swarm.list_dump_services.return_value = {
        "bad-svc": {"fiber.enable": "true"}  # missing host, port, user, dbname, secret
    }
    history = MagicMock(spec=HistoryRepository)
    pool = MagicMock(spec=WorkerPool)
    pool.running_services.return_value = set()
    clock = create_autospec(SystemClock, instance=True)
    clock.now.return_value = datetime(2026, 6, 16, 4, tzinfo=timezone.utc)
    metrics = Metrics(registry=CollectorRegistry())
    stop = asyncio.Event()
    stop.set()
    orchestrator = AsyncMock()
    registry_state = RegistryState()

    from fiber.loop import _scan_loop_inner
    # Should not raise; warning is logged
    await _scan_loop_inner(
        swarm=swarm,
        history=history,
        pool=pool,
        orchestrator=orchestrator,
        clock=clock,
        metrics=metrics,
        stop=stop,
        interval=0,
        registry_state=registry_state,
    )


async def test_scan_loop_updates_registry_state_with_snapshot() -> None:
    """After one scan iteration, registry_state holds the discovered jobs and skipped services."""
    swarm, history, pool, clock, metrics, stop, registry_state = _base_mocks()
    # Add an unenrolled service to be skipped
    swarm.list_dump_services.return_value = {
        "kenku-pg": {
            "fiber.enable": "true",
            "fiber.schedule": "0 3 * * *",
            "fiber.host": "kenku-pg",
            "fiber.port": "5432",
            "fiber.user": "k",
            "fiber.dbname": "k",
            "fiber.secret": "s",
        },
        "traefik": {},  # no fiber.enable — should be skipped
    }
    pool.submit.return_value = asyncio.create_task(asyncio.sleep(0))
    orchestrator = AsyncMock()

    from fiber.loop import _scan_loop_inner
    await _scan_loop_inner(
        swarm=swarm,
        history=history,
        pool=pool,
        orchestrator=orchestrator,
        clock=clock,
        metrics=metrics,
        stop=stop,
        interval=0,
        registry_state=registry_state,
    )

    snap = registry_state.get()
    assert len(snap.jobs) == 1
    assert snap.jobs[0].service == "kenku-pg"
    assert len(snap.skipped) == 1
    assert snap.skipped[0] == ("traefik", "no fiber.enable label")


async def test_scan_loop_sets_scanned_at_on_success() -> None:
    """After a successful scan, snapshot.scanned_at is set to a non-None datetime."""
    swarm, history, pool, clock, metrics, stop, registry_state = _base_mocks()
    pool.submit.return_value = None
    orchestrator = AsyncMock()

    from fiber.loop import _scan_loop_inner
    await _scan_loop_inner(
        swarm=swarm,
        history=history,
        pool=pool,
        orchestrator=orchestrator,
        clock=clock,
        metrics=metrics,
        stop=stop,
        interval=0,
        registry_state=registry_state,
    )

    snap = registry_state.get()
    assert snap.scanned_at is not None
    assert snap.error is None


async def test_scan_loop_preserves_jobs_on_swarm_error() -> None:
    """When swarm.list_dump_services() raises, previous jobs are kept and error is set."""
    from datetime import datetime, timezone

    from fiber.loop import _scan_loop_inner

    # First, seed the registry_state with a known good snapshot
    from fiber.services.registry_state import Snapshot
    from fiber.models import DumpJob
    swarm, history, pool, clock, metrics, _, registry_state = _base_mocks()

    # Pre-seed registry with one job and a scanned_at
    good_job = DumpJobFactory.build(service="kenku-pg")
    good_snap = Snapshot(
        jobs=[good_job],
        misconfigured=[],
        skipped=[],
        scanned_at=datetime(2026, 6, 16, 3, 0, tzinfo=timezone.utc),
        error=None,
    )
    registry_state.set(good_snap)

    # Now swarm raises
    swarm.list_dump_services.side_effect = RuntimeError("docker down")
    stop = asyncio.Event()
    stop.set()
    orchestrator = AsyncMock()

    await _scan_loop_inner(
        swarm=swarm,
        history=history,
        pool=pool,
        orchestrator=orchestrator,
        clock=clock,
        metrics=metrics,
        stop=stop,
        interval=0,
        registry_state=registry_state,
    )

    snap = registry_state.get()
    # Previous jobs preserved
    assert len(snap.jobs) == 1
    assert snap.jobs[0].service == "kenku-pg"
    # scanned_at unchanged (last good scan time)
    assert snap.scanned_at == datetime(2026, 6, 16, 3, 0, tzinfo=timezone.utc)
    # error set
    assert snap.error == "docker down"


async def test_scan_loop_runs_until_stop_is_set() -> None:
    """_scan_loop iterates until stop is set (wired container with overrides)."""
    from fiber.container import Container
    from fiber.loop import _scan_loop
    from fiber.services.registry_state import RegistryState

    c = Container()
    swarm_mock = MagicMock(spec=DockerSwarmGateway)
    swarm_mock.list_dump_services.return_value = {}
    history_mock = MagicMock(spec=HistoryRepository)
    history_mock.last_success.return_value = None
    pool_mock = MagicMock(spec=WorkerPool)
    pool_mock.running_services.return_value = set()
    orchestrator_mock = AsyncMock()
    clock_mock = create_autospec(SystemClock, instance=True)
    clock_mock.now.return_value = datetime(2026, 6, 16, 4, tzinfo=timezone.utc)
    metrics_instance = Metrics(registry=CollectorRegistry())
    config_mock = MagicMock()
    config_mock.scan_interval = 0
    registry_state_instance = RegistryState()

    c.discovery.override(swarm_mock)
    c.history_repository.override(history_mock)
    c.pool.override(pool_mock)
    c.orchestrator.override(orchestrator_mock)
    c.clock.override(clock_mock)
    c.metrics.override(metrics_instance)
    c.config.override(config_mock)
    c.registry_state.override(registry_state_instance)

    c.wire(modules=["fiber.loop"])

    stop = asyncio.Event()

    async def set_stop_soon() -> None:
        await asyncio.sleep(0.01)
        stop.set()

    try:
        await asyncio.gather(_scan_loop(stop), set_stop_soon())
    finally:
        c.unwire()
