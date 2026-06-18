from __future__ import annotations

import asyncio
import contextlib

from dependency_injector.wiring import Provide, inject

from fiber.clock import SystemClock
from fiber.container import Container
from fiber.logger import get_logger
from fiber.metrics import Metrics
from fiber.clients.discovery import DiscoveryProvider
from fiber.clients.probe import ConnectivityProbe
from fiber.registry import reconcile
from fiber.repositories.history import HistoryRepository
from fiber.scheduler import due_jobs
from fiber.services.orchestrator import MovementOrchestrator
from fiber.services.registry_state import RegistryState, Snapshot
from fiber.services.worker_pool import WorkerPool

_logger = get_logger("fiber.main")


async def _scan_loop_inner(
    swarm: DiscoveryProvider,
    history: HistoryRepository,
    pool: WorkerPool,
    orchestrator: MovementOrchestrator,
    clock: SystemClock,
    metrics: Metrics,
    stop: asyncio.Event,
    interval: float,
    registry_state: RegistryState,
    active_provider: str,
    probe: ConnectivityProbe,
) -> None:
    now = clock.now()
    prev = registry_state.get()
    try:
        jobs, misconfigured, skipped = reconcile(swarm.list_dump_services(), active_provider)
    except Exception as exc:
        _logger.error("discovery failed: %s", exc)
        registry_state.set(Snapshot(
            jobs=prev.jobs,
            misconfigured=prev.misconfigured,
            skipped=prev.skipped,
            scanned_at=prev.scanned_at,
            error=str(exc),
        ))
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=interval)
        return
    for m in misconfigured:
        _logger.warning("misconfigured %s: %s", m.service, ", ".join(m.errors))
    registry_state.set(Snapshot(
        jobs=jobs,
        misconfigured=misconfigured,
        skipped=skipped,
        scanned_at=now,
        error=None,
    ))
    last = {j.service: history.last_success(j.service) for j in jobs}
    for job in due_jobs(jobs, clock.now(), last_success={k: v for k, v in last.items() if v},
                        running=pool.running_services()):
        if not (await probe.check(job)).ok:
            metrics.skipped_not_ready.labels(db=job.service).inc()
            _logger.info("deferred %s: database not ready", job.service)
            continue
        result = pool.submit(job.service, lambda j=job: orchestrator.perform(j))
        if result is None:
            metrics.skipped_overlap.labels(db=job.service).inc()
        else:
            _logger.info("enqueued movement for %s", job.service)
    with contextlib.suppress(asyncio.TimeoutError):
        await asyncio.wait_for(stop.wait(), timeout=interval)


@inject
async def _scan_loop(
    stop: asyncio.Event,
    swarm: DiscoveryProvider = Provide[Container.discovery],
    history: HistoryRepository = Provide[Container.history_repository],
    pool: WorkerPool = Provide[Container.pool],
    orchestrator: MovementOrchestrator = Provide[Container.orchestrator],
    clock: SystemClock = Provide[Container.clock],
    metrics: Metrics = Provide[Container.metrics],
    interval: float = Provide[Container.config.provided.scan_interval],
    registry_state: RegistryState = Provide[Container.registry_state],
    active_provider: str = Provide[Container._active_provider],
    probe: ConnectivityProbe = Provide[Container.probe],
) -> None:
    while not stop.is_set():
        await _scan_loop_inner(
            swarm=swarm,
            history=history,
            pool=pool,
            orchestrator=orchestrator,
            clock=clock,
            metrics=metrics,
            stop=stop,
            interval=interval,
            registry_state=registry_state,
            active_provider=active_provider,
            probe=probe,
        )
