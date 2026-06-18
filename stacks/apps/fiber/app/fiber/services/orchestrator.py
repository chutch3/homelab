from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Callable

from fiber.clients.bowl import BowlStorage
from fiber.bristol import classify
from fiber.clock import SystemClock
from fiber.clients.dump_runner import DumpRunner
from fiber.clients.events import EventBroker
from fiber.repositories.history import HistoryRepository
from fiber.metrics import Metrics
from fiber.models import (DumpFormat, DumpJob, Manifest, MovementOutcome, MovementRecord)
from fiber.plunger import plan_sweep
from fiber.clients.secrets import SecretReader
from fiber.clients.swarm import DockerSwarmGateway

_EXT = {DumpFormat.CUSTOM: "dump", DumpFormat.DIRECTORY: "dir", DumpFormat.PLAIN: "sql"}


class MovementOrchestrator:
    def __init__(self, bowl_factory: Callable[[str], BowlStorage], bowl_root: str,
                 secrets: SecretReader, runner: DumpRunner,
                 history: HistoryRepository, swarm: DockerSwarmGateway, clock: SystemClock,
                 fiber_version: str, metrics: Metrics, events: EventBroker) -> None:
        self._bowl_factory = bowl_factory
        self._bowl_root = bowl_root
        self._secrets = secrets
        self._runner = runner
        self._history = history
        self._swarm = swarm
        self._clock = clock
        self._version = fiber_version
        self._metrics = metrics
        self._events = events

    async def perform(self, job: DumpJob) -> MovementRecord:
        self._metrics.in_progress.labels(db=job.service).inc()
        await self._events.publish(job.service)
        try:
            return await self._perform(job)
        finally:
            self._metrics.in_progress.labels(db=job.service).dec()

    async def _perform(self, job: DumpJob) -> MovementRecord:
        bowl = self._bowl_factory(job.path or self._bowl_root)
        started = self._clock.now()
        ts = started.strftime("%Y%m%dT%H%M%S")
        baseline = self._history.median_bytes(job.service, limit=10) or 0
        required = max(baseline * 2, 1)

        if not bowl.has_room(required_bytes=required):
            finished = self._clock.now()
            return await self._finish(job, started, finished, MovementOutcome.CLOGGED, 0, None,
                                      bowl.write_sample(job.service, ts, "no room in the Bowl"), None)

        password = self._secrets.read(job.secret)
        temp = bowl.temp_path(job.service, ts, _EXT[job.fmt])
        outcome = await self._runner.run(job, password=password, out_path=temp)

        if outcome.cancelled:
            self._sweep(job, bowl)
            finished = self._clock.now()
            return await self._finish(job, started, finished, MovementOutcome.PINCHED, 0, None, None, None)
        if outcome.returncode != 0:
            sample = bowl.write_sample(job.service, ts, outcome.stderr_tail)
            self._sweep(job, bowl)
            finished = self._clock.now()
            return await self._finish(job, started, finished, MovementOutcome.CLOGGED, 0, None, sample, None)

        final = bowl.promote(temp)
        size = bowl.size(final)
        sha = bowl.checksum(final)
        bristol = classify(size, baseline or None)
        image, digest = self._swarm.image_of(job.app) if job.app else (None, None)
        finished = self._clock.now()
        manifest = Manifest(service=job.service, engine=job.engine, server_version="",
                            app_service=job.app, app_image=image, app_digest=digest,
                            fmt=job.fmt, jobs=job.jobs, bytes=size, sha256=sha,
                            fiber_version=self._version, schema_marker=None,
                            finished_at=finished.isoformat())
        receipt = bowl.write_receipt(final, asdict(manifest))
        self._sweep(job, bowl)
        return await self._finish(job, started, finished, MovementOutcome.CLEAN, size, bristol, None,
                                  receipt, image, digest)

    def _sweep(self, job: DumpJob, bowl: BowlStorage) -> None:
        to_delete, dingleberries = plan_sweep(bowl.list_entries(job.service), job.retain)
        for entry in (*to_delete, *dingleberries):
            bowl.delete(entry.path)

    async def _finish(self, job: DumpJob, started: datetime, finished: datetime,
                      outcome: MovementOutcome, size: int,
                      bristol: int | None, sample: str | None, receipt: str | None,
                      image: str | None = None, digest: str | None = None) -> MovementRecord:
        rec = MovementRecord(service=job.service, engine=job.engine, started_at=started,
                             finished_at=finished, outcome=outcome, bytes_written=size,
                             bristol_type=bristol, sample_path=sample, receipt_path=receipt,
                             app_image=image, app_digest=digest)
        self._history.record(rec)
        self._metrics.record_outcome(
            job.service, outcome,
            duration_s=(finished - started).total_seconds(),
            nbytes=size,
            ts=finished.timestamp(),
        )
        await self._events.publish(job.service)
        return rec
