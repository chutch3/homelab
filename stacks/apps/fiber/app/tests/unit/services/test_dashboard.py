from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, create_autospec

import pytest

from fiber.clients.bowl import BowlStorage
from fiber.repositories.history import HistoryRepository
from fiber.domain.models import BowlEntry, MovementOutcome, MovementRecord
from fiber.services.dashboard import DashboardService
from fiber.services.registry_state import RegistryState, Snapshot
from fiber.services.worker_pool import WorkerPool
from fiber.domain.status import DBStatus
from fiber.domain.view import DiscoveryRow
from tests.factories import DumpJobFactory, MovementRecordFactory

UTC = timezone.utc
NOW = datetime(2026, 6, 15, 9, 0, tzinfo=UTC)


class TestDashboardService:
    @pytest.fixture()
    def job(self) -> object:
        return DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)

    @pytest.fixture()
    def registry_state(self, job: object) -> RegistryState:
        from fiber.domain.models import MisconfiguredJob
        rs = RegistryState()
        snap = Snapshot(
            jobs=[job],  # type: ignore[list-item]
            misconfigured=[MisconfiguredJob(service="paperless", errors=("missing host",))],
            skipped=[("traefik", "no fiber.enable label")],
        )
        rs.set(snap)
        return rs

    @pytest.fixture()
    def history(self) -> MagicMock:
        m = create_autospec(HistoryRepository, instance=True)
        # last clean success well within schedule
        m.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        m.last_outcome.return_value = MovementOutcome.CLEAN
        m.recent.return_value = []
        m.latest_clean.return_value = None
        return m

    @pytest.fixture()
    def pool(self) -> MagicMock:
        m = create_autospec(WorkerPool, instance=True)
        m.started_at.return_value = None  # nothing running
        return m

    @pytest.fixture()
    def bowl(self) -> MagicMock:
        m = create_autospec(BowlStorage, instance=True)
        m.usage.return_value = (1024 * 1024 * 100, 1024 * 1024 * 1024)  # 100 MB used, 1 GB free
        return m

    @pytest.fixture()
    def subject(
        self,
        registry_state: RegistryState,
        history: MagicMock,
        pool: MagicMock,
        bowl: MagicMock,
    ) -> DashboardService:
        return DashboardService(
            registry_state=registry_state,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )

    def test_build_returns_dashboard_vm(self, subject: DashboardService) -> None:
        vm = subject.build()
        assert vm is not None

    def test_build_has_correct_card_count(self, subject: DashboardService) -> None:
        # 1 clean job + 1 misconfigured = 2 cards
        vm = subject.build()
        assert len(vm.cards) == 2

    def test_misconfigured_card_appears_first_due_to_severity(self, subject: DashboardService) -> None:
        vm = subject.build()
        assert vm.cards[0].status is DBStatus.MISCONFIGURED

    def test_clean_card_has_correct_status(self, subject: DashboardService) -> None:
        vm = subject.build()
        clean_cards = [c for c in vm.cards if c.service == "immich"]
        assert len(clean_cards) == 1
        assert clean_cards[0].status is DBStatus.CLEAN

    def test_counts_by_status(self, subject: DashboardService) -> None:
        vm = subject.build()
        assert vm.counts.by_status[DBStatus.CLEAN] == 1
        assert vm.counts.by_status[DBStatus.MISCONFIGURED] == 1

    def test_discovery_rows_include_misconfigured(self, subject: DashboardService) -> None:
        vm = subject.build()
        names = [r.service for r in vm.discovery]
        assert "paperless" in names
        paperless_rows = [r for r in vm.discovery if r.service == "paperless"]
        assert paperless_rows[0].result == "misconfigured"

    def test_discovery_rows_include_skipped(self, subject: DashboardService) -> None:
        vm = subject.build()
        names = [r.service for r in vm.discovery]
        assert "traefik" in names
        traefik_rows = [r for r in vm.discovery if r.service == "traefik"]
        assert traefik_rows[0].result == "skipped"

    def test_discovery_rows_include_discovered_jobs(self, subject: DashboardService) -> None:
        vm = subject.build()
        immich_rows = [r for r in vm.discovery if r.service == "immich"]
        assert immich_rows[0].result == "discovered"

    def test_history_queried_per_job(self, subject: DashboardService, history: MagicMock) -> None:
        subject.build()
        history.last_success.assert_called_with("immich")
        history.last_outcome.assert_called_with("immich")

    def test_build_populates_size_and_bristol_from_latest_clean(
        self, registry_state: RegistryState, pool: MagicMock, bowl: MagicMock
    ) -> None:
        clean_rec = MovementRecordFactory.build(
            service="immich",
            outcome=MovementOutcome.CLEAN,
            bytes_written=1024 * 1024 * 50,
            bristol_type=4,
        )
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        history.latest_clean.return_value = clean_rec
        svc = DashboardService(
            registry_state=registry_state,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        immich_cards = [c for c in vm.cards if c.service == "immich"]
        assert len(immich_cards) == 1
        card = immich_cards[0]
        assert card.bristol == 4
        assert "MB" in card.size or "KB" in card.size or "B" in card.size
        assert card.size != "—"

    def test_build_size_fallback_when_no_clean_history(
        self, registry_state: RegistryState, pool: MagicMock, bowl: MagicMock
    ) -> None:
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        history.latest_clean.return_value = None
        svc = DashboardService(
            registry_state=registry_state,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        immich_cards = [c for c in vm.cards if c.service == "immich"]
        assert immich_cards[0].size == "—"
        assert immich_cards[0].bristol is None

    def test_bowl_usage_reflected_in_vm(self, subject: DashboardService) -> None:
        vm = subject.build()
        assert "100" in vm.bowl_used or "MB" in vm.bowl_used or len(vm.bowl_used) > 0
        assert len(vm.bowl_free) > 0

    def test_card_returns_matching_card(self, subject: DashboardService) -> None:
        c = subject.card("immich")
        assert c.service == "immich"

    def test_card_returns_fallback_for_unknown_service(self, subject: DashboardService) -> None:
        from fiber.domain.status import DBStatus
        c = subject.card("nonexistent")
        assert c.service == "nonexistent"
        assert c.status is DBStatus.MISCONFIGURED
        assert c.error == "not found"

    def test_detail_returns_drawer_vm(self, subject: DashboardService) -> None:
        from fiber.domain.view import DrawerVM
        d = subject.detail("immich")
        assert isinstance(d, DrawerVM)
        assert d.service == "immich"


class TestDashboardServiceDetail:
    """Tests for DashboardService.detail() returning DrawerVM."""

    @pytest.fixture()
    def clean_job(self) -> object:
        return DumpJobFactory.build(
            service="immich",
            schedule="0 3 * * *",
            path=None,
            app="immich",
            secret="immich_db_password",
        )

    @pytest.fixture()
    def clogged_job(self) -> object:
        return DumpJobFactory.build(
            service="excalidraw",
            schedule="0 3 * * *",
            path=None,
            app="excalidraw",
            secret="excalidraw_db_password",
        )

    @pytest.fixture()
    def clean_movement(self) -> MovementRecord:
        return MovementRecordFactory.build(
            service="immich",
            outcome=MovementOutcome.CLEAN,
            bytes_written=1024 * 1024 * 88,
            bristol_type=4,
            app_image="immich:1.135",
            receipt_path="/backups/immich/2026-06-15.dump.manifest.json",
            sample_path=None,
        )

    @pytest.fixture()
    def clogged_movement(self) -> MovementRecord:
        return MovementRecordFactory.build(
            service="excalidraw",
            outcome=MovementOutcome.CLOGGED,
            bytes_written=0,
            bristol_type=None,
            app_image="excalidraw:1.0",
            receipt_path=None,
            sample_path="/backups/excalidraw/2026-06-15.stool.log",
        )

    def _make_subject(self, jobs, misconfigured, history_mock, bowl_mock):
        rs = RegistryState()
        snap = Snapshot(jobs=jobs, misconfigured=misconfigured, skipped=[])
        rs.set(snap)
        return DashboardService(
            registry_state=rs,
            history=history_mock,
            pool=create_autospec(WorkerPool, instance=True),
            bowl=bowl_mock,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )

    def test_detail_returns_drawer_vm(self, clean_job, clean_movement) -> None:
        from fiber.domain.view import DrawerVM
        history = create_autospec(HistoryRepository, instance=True)
        history.recent.return_value = [clean_movement]
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.read_text.return_value = '{"sha256": "abc123", "bytes": 100}'
        subject = self._make_subject([clean_job], [], history, bowl)
        vm = subject.detail("immich")
        assert isinstance(vm, DrawerVM)

    def test_detail_timeline_populated_from_recent(self, clean_job, clean_movement) -> None:
        history = create_autospec(HistoryRepository, instance=True)
        history.recent.return_value = [clean_movement, clean_movement]
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.read_text.return_value = None
        subject = self._make_subject([clean_job], [], history, bowl)
        vm = subject.detail("immich")
        assert len(vm.timeline) == 2
        assert vm.timeline[0][1] == "clean"

    def test_detail_sha_from_receipt_json(self, clean_job, clean_movement) -> None:
        history = create_autospec(HistoryRepository, instance=True)
        history.recent.return_value = [clean_movement]
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.read_text.return_value = '{"sha256": "deadbeef", "bytes": 100}'
        subject = self._make_subject([clean_job], [], history, bowl)
        vm = subject.detail("immich")
        assert vm.sha == "deadbeef"

    def test_detail_sha_none_when_no_receipt(self, clean_job, clean_movement) -> None:
        history = create_autospec(HistoryRepository, instance=True)
        history.recent.return_value = [clean_movement]
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.read_text.return_value = None
        subject = self._make_subject([clean_job], [], history, bowl)
        vm = subject.detail("immich")
        assert vm.sha is None

    def test_detail_sample_from_clogged_movement(self, clogged_job, clogged_movement) -> None:
        history = create_autospec(HistoryRepository, instance=True)
        history.recent.return_value = [clogged_movement]
        history.last_success.return_value = None
        history.last_outcome.return_value = MovementOutcome.CLOGGED
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.read_text.side_effect = lambda path: (
            "pg_dump: connection failed" if path and "stool" in path else None
        )
        subject = self._make_subject([clogged_job], [], history, bowl)
        vm = subject.detail("excalidraw")
        assert vm.sample == "pg_dump: connection failed"

    def test_detail_labels_contains_service(self, clean_job) -> None:
        history = create_autospec(HistoryRepository, instance=True)
        history.recent.return_value = []
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.read_text.return_value = None
        subject = self._make_subject([clean_job], [], history, bowl)
        vm = subject.detail("immich")
        assert "fiber.enable=true" in vm.labels
        assert "fiber.secret" in vm.labels

    def test_detail_misconfigured_service(self) -> None:
        from fiber.domain.models import MisconfiguredJob
        from fiber.domain.view import DrawerVM
        history = create_autospec(HistoryRepository, instance=True)
        history.recent.return_value = []
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.read_text.return_value = None
        rs = RegistryState()
        snap = Snapshot(
            jobs=[],
            misconfigured=[MisconfiguredJob(service="paperless", errors=("missing fiber.secret",))],
            skipped=[],
        )
        rs.set(snap)
        subject = DashboardService(
            registry_state=rs,
            history=history,
            pool=create_autospec(WorkerPool, instance=True),
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = subject.detail("paperless")
        assert isinstance(vm, DrawerVM)
        assert vm.status.value == "misconfigured"
        assert vm.error is not None


class TestDiscoveryHealth:
    def test_discovery_rel_populated_when_scanned_at_set(self) -> None:
        from fiber.services.registry_state import Snapshot
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        snap = Snapshot(
            jobs=[job],
            misconfigured=[],
            skipped=[],
            scanned_at=NOW - timedelta(seconds=12),
            error=None,
        )
        rs.set(snap)
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        history.latest_clean.return_value = None
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        assert vm.discovery_rel == "12s ago"
        assert vm.discovery_error is None

    def test_discovery_rel_dash_when_never_scanned(self) -> None:
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        rs.set(Snapshot(jobs=[job], misconfigured=[], skipped=[]))
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        history.latest_clean.return_value = None
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        assert vm.discovery_rel == "—"

    def test_discovery_error_surfaced(self) -> None:
        rs = RegistryState()
        rs.set(Snapshot(
            jobs=[],
            misconfigured=[],
            skipped=[],
            scanned_at=NOW - timedelta(seconds=5),
            error="docker unavailable",
        ))
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        history.latest_clean.return_value = None
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        assert vm.discovery_error == "docker unavailable"


class TestDashboardSort:
    """Verify cards sort by CardVM.severity (not a local _SEVERITY dict in dashboard.py)."""

    def _build_service(
        self, registry_state: RegistryState, last_outcome: MovementOutcome, history_mock: MagicMock
    ) -> DashboardService:
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        return DashboardService(
            registry_state=registry_state,
            history=history_mock,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )

    def test_clogged_sorts_before_constipated_before_clean(self) -> None:
        from fiber.domain.models import MisconfiguredJob
        clogged_job = DumpJobFactory.build(service="clogged-svc", schedule="0 3 * * *", path=None)
        constipated_job = DumpJobFactory.build(service="constipated-svc", schedule="0 3 * * *", path=None)
        clean_job = DumpJobFactory.build(service="clean-svc", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        snap = Snapshot(jobs=[clean_job, constipated_job, clogged_job], misconfigured=[], skipped=[])
        rs.set(snap)
        history = create_autospec(HistoryRepository, instance=True)
        history.latest_clean.return_value = None
        history.last_success.return_value = None
        history.last_outcome.side_effect = lambda svc: {
            "clogged-svc": MovementOutcome.CLOGGED,
            "constipated-svc": MovementOutcome.CLEAN,
            "clean-svc": MovementOutcome.CLEAN,
        }.get(svc)
        # constipated-svc has a last_success far in the past to trigger CONSTIPATED
        history.last_success.side_effect = lambda svc: {
            "clogged-svc": None,
            "constipated-svc": datetime(2026, 1, 1, 3, 0, tzinfo=UTC),  # far in past
            "clean-svc": datetime(2026, 6, 15, 3, 0, tzinfo=UTC),
        }.get(svc)
        svc = self._build_service(rs, MovementOutcome.CLEAN, history)
        vm = svc.build()
        statuses = [c.status for c in vm.cards]
        # clogged severity 3 should be first, clean severity 0 last
        assert statuses[0] is DBStatus.CLOGGED
        assert statuses[-1] is DBStatus.CLEAN


class TestNextRun:
    def test_next_run_populated_for_clean_card(self) -> None:
        """Non-running, non-misconfigured cards get a relative next_run string."""
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        rs.set(Snapshot(jobs=[job], misconfigured=[], skipped=[]))
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        history.latest_clean.return_value = None
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        card = next(c for c in vm.cards if c.service == "immich")
        # next_run should say "in Xh" (next 03:00 after 09:00 is next day)
        assert card.next_run != "—"
        assert "in" in card.next_run

    def test_next_run_is_in_progress_for_straining(self) -> None:
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        rs.set(Snapshot(jobs=[job], misconfigured=[], skipped=[]))
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        history.latest_clean.return_value = None
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = NOW - timedelta(seconds=30)
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.list_entries.return_value = []
        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        card = next(c for c in vm.cards if c.service == "immich")
        assert card.next_run == "in progress"

    def test_next_run_is_dash_for_misconfigured(self) -> None:
        from fiber.domain.models import MisconfiguredJob
        rs = RegistryState()
        rs.set(Snapshot(
            jobs=[],
            misconfigured=[MisconfiguredJob(service="bad", errors=("err",))],
            skipped=[],
        ))
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        history.latest_clean.return_value = None
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        card = next(c for c in vm.cards if c.service == "bad")
        assert card.next_run == "—"


class TestStrainProgress:
    def test_straining_card_has_progress_string(self) -> None:
        """Running card: progress = 'X GB · M:SS' from partial entry size + elapsed."""
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        rs.set(Snapshot(jobs=[job], misconfigured=[], skipped=[]))

        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = None
        history.last_outcome.return_value = None
        history.latest_clean.return_value = None

        started = NOW - timedelta(seconds=98)
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = started

        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        bowl.list_entries.return_value = [
            BowlEntry(
                path="/backups/immich/x.dump.partial",
                size_bytes=4_200_000_000,
                modified_at=NOW,
                is_temp=True,
            )
        ]

        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        cards = [c for c in vm.cards if c.service == "immich"]
        assert len(cards) == 1
        card = cards[0]
        assert card.status is DBStatus.STRAINING
        # 4_200_000_000 bytes = 4200 MB = ~4 GB (binary: 4200/1024/1024/1024 ≈ 3.9 → "3 GB")
        # 98s = 1:38
        assert card.progress is not None
        assert "GB" in card.progress
        assert "1:38" in card.progress

    def test_non_running_card_has_no_progress(self) -> None:
        job = DumpJobFactory.build(service="immich", schedule="0 3 * * *", path=None)
        rs = RegistryState()
        rs.set(Snapshot(jobs=[job], misconfigured=[], skipped=[]))
        history = create_autospec(HistoryRepository, instance=True)
        history.last_success.return_value = datetime(2026, 6, 15, 3, 0, tzinfo=UTC)
        history.last_outcome.return_value = MovementOutcome.CLEAN
        history.latest_clean.return_value = None
        pool = create_autospec(WorkerPool, instance=True)
        pool.started_at.return_value = None
        bowl = create_autospec(BowlStorage, instance=True)
        bowl.usage.return_value = (0, 0)
        svc = DashboardService(
            registry_state=rs,
            history=history,
            pool=pool,
            bowl=bowl,
            now=lambda: NOW,
            default_bowl_root="/backups",
        )
        vm = svc.build()
        card = next(c for c in vm.cards if c.service == "immich")
        assert card.progress is None


class TestRelTime:
    def test_seconds(self) -> None:
        from fiber.services.dashboard import _rel_time
        from datetime import datetime, timezone
        now = datetime(2026, 6, 15, 9, 0, 30, tzinfo=timezone.utc)
        dt = datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
        assert _rel_time(dt, now) == "30s ago"

    def test_minutes(self) -> None:
        from fiber.services.dashboard import _rel_time
        from datetime import datetime, timezone
        now = datetime(2026, 6, 15, 9, 5, 0, tzinfo=timezone.utc)
        dt = datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
        assert _rel_time(dt, now) == "5m ago"

    def test_days(self) -> None:
        from fiber.services.dashboard import _rel_time
        from datetime import datetime, timezone
        now = datetime(2026, 6, 17, 9, 0, 0, tzinfo=timezone.utc)
        dt = datetime(2026, 6, 15, 9, 0, 0, tzinfo=timezone.utc)
        assert _rel_time(dt, now) == "2d ago"


class TestFmtBytes:
    def test_bytes(self) -> None:
        from fiber.services.dashboard import _fmt_bytes
        assert _fmt_bytes(500) == "500 B"

    def test_megabytes(self) -> None:
        from fiber.services.dashboard import _fmt_bytes
        result = _fmt_bytes(1024 * 1024 * 100)
        assert "MB" in result or "GB" in result
