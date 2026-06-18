from __future__ import annotations

import inspect
from datetime import datetime, timezone
from unittest.mock import MagicMock, create_autospec

import pytest
from prometheus_client import CollectorRegistry

from fiber.clients.bowl import BowlStorage
from fiber.clients.events import EventBroker
from fiber.clock import SystemClock
from fiber.clients.dump_runner import DumpRunner, RunOutcome
from fiber.repositories.history import HistoryRepository
from fiber.metrics import Metrics
from fiber.models import DumpFormat, DumpJob, Engine, MovementOutcome
from fiber.services.orchestrator import MovementOrchestrator
from fiber.clients.secrets import SecretReader
from fiber.clients.swarm import DockerSwarmGateway
from tests.factories import DumpJobFactory


class TestMovementOrchestrator:
    @pytest.fixture()
    def bowl(self) -> MagicMock:
        m = MagicMock(spec=BowlStorage)
        m.has_room.return_value = True
        m.temp_path.return_value = "/bowl/kenku-pg/ts.dump.partial"
        m.promote.return_value = "/bowl/kenku-pg/ts.dump"
        m.size.return_value = 2048
        m.checksum.return_value = "abc"
        m.list_entries.return_value = []
        return m

    @pytest.fixture()
    def bowl_factory(self, bowl: MagicMock) -> MagicMock:
        return MagicMock(return_value=bowl)

    @pytest.fixture()
    def secrets(self) -> MagicMock:
        m = MagicMock(spec=SecretReader)
        m.read.return_value = "pw"
        return m

    @pytest.fixture()
    def runner(self) -> MagicMock:
        m = create_autospec(DumpRunner, instance=True)
        m.run.return_value = RunOutcome(0, "", False)
        return m

    @pytest.fixture()
    def history(self) -> MagicMock:
        m = MagicMock(spec=HistoryRepository)
        m.median_bytes.return_value = None
        return m

    @pytest.fixture()
    def swarm(self) -> MagicMock:
        m = MagicMock(spec=DockerSwarmGateway)
        m.image_of.return_value = ("img:1", "sha256:d")
        return m

    @pytest.fixture()
    def clock(self) -> MagicMock:
        m = create_autospec(SystemClock, instance=True)
        m.now.return_value = datetime(2026, 6, 15, 3, tzinfo=timezone.utc)
        return m

    @pytest.fixture()
    def metrics(self) -> Metrics:
        return Metrics(registry=CollectorRegistry())

    @pytest.fixture()
    def broker(self) -> MagicMock:
        return create_autospec(EventBroker, instance=True)

    @pytest.fixture()
    def subject(
        self,
        bowl_factory: MagicMock,
        secrets: MagicMock,
        runner: MagicMock,
        history: MagicMock,
        swarm: MagicMock,
        clock: MagicMock,
        metrics: Metrics,
        broker: MagicMock,
    ) -> MovementOrchestrator:
        return MovementOrchestrator(
            bowl_factory=bowl_factory, bowl_root="/backups",
            secrets=secrets, runner=runner, history=history,
            discovery=swarm, clock=clock, fiber_version="0.1.0", metrics=metrics,
            events=broker,
        )

    async def test_clean_movement_promotes_and_records(
        self, subject: MovementOrchestrator, bowl: MagicMock, runner: MagicMock, history: MagicMock
    ) -> None:
        rec = await subject.perform(DumpJobFactory.build(app="downloads_kenku", dbname="k", user="k"))
        assert rec.outcome is MovementOutcome.CLEAN
        assert rec.bytes_written == 2048
        bowl.promote.assert_called_once()
        bowl.size.assert_called_once_with("/bowl/kenku-pg/ts.dump")
        bowl.write_receipt.assert_called_once()
        history.record.assert_called_once()

    async def test_no_room_is_clogged_before_dumping(
        self, subject: MovementOrchestrator, bowl: MagicMock, runner: MagicMock
    ) -> None:
        bowl.has_room.return_value = False
        rec = await subject.perform(DumpJobFactory.build(app="downloads_kenku", dbname="k", user="k"))
        assert rec.outcome is MovementOutcome.CLOGGED
        runner.run.assert_not_called()

    async def test_failed_dump_is_clogged_and_swept(
        self, subject: MovementOrchestrator, bowl: MagicMock, runner: MagicMock
    ) -> None:
        runner.run.return_value = RunOutcome(returncode=1, stderr_tail="boom", cancelled=False)
        rec = await subject.perform(DumpJobFactory.build(app="downloads_kenku", dbname="k", user="k"))
        assert rec.outcome is MovementOutcome.CLOGGED
        bowl.promote.assert_not_called()
        bowl.write_sample.assert_called_once()

    async def test_cancelled_dump_is_pinched(
        self, subject: MovementOrchestrator, runner: MagicMock
    ) -> None:
        runner.run.return_value = RunOutcome(returncode=-1, stderr_tail="cancelled", cancelled=True)
        rec = await subject.perform(DumpJobFactory.build(app="downloads_kenku", dbname="k", user="k"))
        assert rec.outcome is MovementOutcome.PINCHED

    async def test_clean_movement_records_metrics(
        self, subject: MovementOrchestrator, metrics: Metrics
    ) -> None:
        registry = metrics.registry
        await subject.perform(DumpJobFactory.build(app="downloads_kenku", dbname="k", user="k"))
        count = registry.get_sample_value("fiber_movements_total", {"db": "kenku-pg", "status": "clean"})
        assert count == 1.0
        size_val = registry.get_sample_value("fiber_movement_bytes", {"db": "kenku-pg"})
        assert size_val == 2048.0

    async def test_clogged_movement_records_metrics(
        self, subject: MovementOrchestrator, bowl: MagicMock, metrics: Metrics
    ) -> None:
        registry = metrics.registry
        bowl.has_room.return_value = False
        await subject.perform(DumpJobFactory.build(app="downloads_kenku", dbname="k", user="k"))
        count = registry.get_sample_value("fiber_movements_total", {"db": "kenku-pg", "status": "clogged"})
        assert count == 1.0

    def test_finish_has_datetime_annotation_and_no_bristol_path(self) -> None:
        import typing
        hints = typing.get_type_hints(MovementOrchestrator._finish)
        sig = inspect.signature(MovementOrchestrator._finish)
        params = sig.parameters
        assert "bristol_path" not in params, "bristol_path param must be removed from _finish"
        assert hints.get("started") is datetime, f"started must be annotated as datetime, got {hints.get('started')}"

    async def test_no_fiber_path_uses_bowl_root(
        self, subject: MovementOrchestrator, bowl_factory: MagicMock
    ) -> None:
        await subject.perform(DumpJobFactory.build(app=None, dbname="k", user="k", path=None))
        bowl_factory.assert_called_once_with("/backups")

    async def test_fiber_path_overrides_bowl_root(
        self, subject: MovementOrchestrator, bowl_factory: MagicMock
    ) -> None:
        await subject.perform(DumpJobFactory.build(app=None, dbname="k", user="k", path="/mnt/big/x"))
        bowl_factory.assert_called_once_with("/mnt/big/x")

    async def test_perform_publishes_event_to_broker(
        self, subject: MovementOrchestrator, broker: MagicMock
    ) -> None:
        job = DumpJobFactory.build(app="downloads_kenku", dbname="k", user="k")
        await subject.perform(job)
        assert broker.publish.await_count >= 1
        broker.publish.assert_any_await(job.service)
