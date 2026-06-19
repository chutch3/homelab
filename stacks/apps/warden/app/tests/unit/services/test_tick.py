from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest
from prometheus_client import CollectorRegistry

from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.models import ArrType, QueueItem, SourceQuota
from warden.repositories.ledger import SearchLedgerRepository
from warden.schedule import ResetSchedule
from warden.services.orchestrator import TickOrchestrator
from warden.services.pacer import Pacer
from warden.services.planner import HuntPlanner
from warden.services.quota import QuotaLedger
from warden.services.quota_source import FallbackQuotaSource
from warden.services.stale import StaleDetector
from warden.services.sweeper import QueueSweeper
from tests.factories import FakeArrClient, missing_item


def _sweeper() -> QueueSweeper:
    return QueueSweeper(StaleDetector(grace_hours=48), enabled=True, max_removals_per_tick=5,
                        mass_fraction=0.5, min_queue_for_guard=3)


class FrozenClock(SystemClock):
    def __init__(self, when: datetime) -> None:
        self._when = when

    def now(self) -> datetime:
        return self._when


NOON = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)


class StubQuotaSource:
    def __init__(self, limits: dict[ArrType, int]) -> None:
        self._limits = limits

    async def quotas(self) -> dict[ArrType, SourceQuota]:
        return {
            arr_type: SourceQuota(
                gross_limit=gross,
                mode="prowlarr",
                indexers_total=3,
                indexers_defaulted=1,
            )
            for arr_type, gross in self._limits.items()
        }


class _BoomQuotaSource:
    async def quotas(self) -> dict[ArrType, SourceQuota]:
        raise RuntimeError("prowlarr down")


class TestTickOrchestrator:
    @pytest.fixture()
    def make(self, repo: SearchLedgerRepository) -> Callable[..., tuple[TickOrchestrator, Metrics]]:
        def _make(clients, *, quota_source=None, fallback=200, reserve=20, poll=300, when=NOON,
                  prowlarr_fallback_on_error=True):
            schedule = ResetSchedule("00:00")
            metrics = Metrics(CollectorRegistry())
            orch = TickOrchestrator(
                clients=clients,
                quota=QuotaLedger(reserve_pct=reserve, fallback_budget=fallback, schedule=schedule),
                pacer=Pacer(poll_interval_sec=poll),
                planner=HuntPlanner(),
                sweeper=_sweeper(),
                ledger=repo,
                clock=FrozenClock(when),
                metrics=metrics,
                schedule=schedule,
                quota_source=quota_source or FallbackQuotaSource(),
                include_cutoff_unmet=True,
                fallback_per_day=fallback,
                poll_interval_sec=poll,
                prowlarr_fallback_on_error=prowlarr_fallback_on_error,
            )
            return orch, metrics
        return _make

    async def test_fallback_mode_paces_each_source(self, make):
        radarr = FakeArrClient("radarr", [missing_item("radarr", i) for i in range(50)], arr_type=ArrType.RADARR)
        orch, _ = make([radarr])
        decision = await orch.tick()
        # fallback 200 * 0.8 = 160 over 144 ticks (12:00->reset) => floor=1
        assert sum(len(s) for s in radarr.searched) == 1
        assert decision.reason == "paced"

    async def test_prowlarr_limits_drive_per_source_budget_independently(self, make, repo):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        sonarr = FakeArrClient("sonarr", [missing_item("sonarr", 9)], arr_type=ArrType.SONARR)
        qs = StubQuotaSource({ArrType.RADARR: 100, ArrType.SONARR: 100})
        # radarr already spent its whole budget (100*0.8=80) today -> blocked; sonarr fresh
        orch, _ = make([radarr, sonarr], quota_source=qs)
        repo.add(f"radarr:{ResetSchedule('00:00').window_key(NOON)}", 80)
        decision = await orch.tick()
        assert radarr.searched == []          # radarr paused
        assert sonarr.searched == [[9]]        # sonarr still hunts
        assert decision.reason == "paced"

    async def test_all_sources_blocked_sleeps_until_reset(self, make, repo):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        qs = StubQuotaSource({ArrType.RADARR: 100})
        orch, _ = make([radarr], quota_source=qs)
        repo.add(f"radarr:{ResetSchedule('00:00').window_key(NOON)}", 80)
        decision = await orch.tick()
        assert radarr.searched == []
        assert decision.reason == "blocked"
        assert decision.seconds > 0

    async def test_source_with_zero_indexers_is_blocked(self, make):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        qs = StubQuotaSource({ArrType.RADARR: 0})
        orch, _ = make([radarr], quota_source=qs)
        decision = await orch.tick()
        assert radarr.searched == []
        assert decision.reason == "blocked"

    async def test_unreachable_source_does_not_block_the_other(self, make):
        bad = FakeArrClient("radarr", [missing_item("radarr", 1)], raises=True, arr_type=ArrType.RADARR)
        good = FakeArrClient("sonarr", [missing_item("sonarr", 9)], arr_type=ArrType.SONARR)
        orch, _ = make([bad, good], when=datetime(2026, 6, 16, 23, 59, tzinfo=timezone.utc))
        decision = await orch.tick()
        assert bad.searched == []          # unreachable -> nothing issued
        assert good.searched == [[9]]      # the other source still hunts
        assert decision.reason == "paced"

    async def test_quota_source_error_falls_back_when_enabled(self, make):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        orch, _ = make([radarr], quota_source=_BoomQuotaSource(), fallback=200)
        decision = await orch.tick()
        assert radarr.searched == [[1]]      # fell back to flat budget, still hunts
        assert decision.reason == "paced"

    async def test_quota_source_error_raises_when_fallback_disabled(self, make):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        orch, _ = make([radarr], quota_source=_BoomQuotaSource(), prowlarr_fallback_on_error=False)
        with pytest.raises(RuntimeError):
            await orch.tick()

    async def test_prowlarr_tick_sets_provenance_metrics(self, make):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        qs = StubQuotaSource({ArrType.RADARR: 500})
        orch, metrics = make([radarr], quota_source=qs)
        await orch.tick()
        reg = metrics.registry
        assert reg.get_sample_value("warden_binding_query_limit", {"source": "radarr"}) == 500
        assert reg.get_sample_value("warden_quota_prowlarr", {"source": "radarr"}) == 1
        assert reg.get_sample_value("warden_indexers_total", {"source": "radarr"}) == 3
        assert reg.get_sample_value("warden_indexers_defaulted", {"source": "radarr"}) == 1

    async def test_fallback_tick_sets_quota_prowlarr_zero(self, make):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        # FallbackQuotaSource returns empty dict -> no SourceQuota -> prowlarr=0
        orch, metrics = make([radarr], quota_source=FallbackQuotaSource())
        await orch.tick()
        assert metrics.registry.get_sample_value("warden_quota_prowlarr", {"source": "radarr"}) == 0

    async def test_blocked_tick_increments_paused_ticks_and_sets_last_tick(self, make, repo):
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        qs = StubQuotaSource({ArrType.RADARR: 100})
        orch, metrics = make([radarr], quota_source=qs)
        repo.add(f"radarr:{ResetSchedule('00:00').window_key(NOON)}", 80)
        decision = await orch.tick()
        assert decision.reason == "blocked"
        reg = metrics.registry
        assert reg.get_sample_value("warden_paused_ticks_total", {"source": "radarr"}) == 1
        assert reg.get_sample_value("warden_last_tick_timestamp_seconds", {}) == NOON.timestamp()

    async def test_removes_stale_and_excludes_queued_from_hunt(self, make):
        # movie 1 is stale-in-queue; movie 2 is healthy-downloading (in queue, not stale)
        radarr = FakeArrClient(
            "radarr",
            [missing_item("radarr", 1), missing_item("radarr", 2), missing_item("radarr", 3)],
            arr_type=ArrType.RADARR,
            queue=[
                QueueItem(id=11, remote_id=1, title="stale", status="warning",
                          error_message="stalled with no connections", added=NOON - timedelta(hours=72)),
                QueueItem(id=12, remote_id=2, title="dl", status="downloading",
                          error_message="", added=NOON - timedelta(hours=1)),
            ],
        )
        orch, metrics = make([radarr])
        await orch.tick()
        # stale movie 1 removed+blocklisted
        assert radarr.removed == [11]
        # movie 2 (in queue, downloading) excluded from search; movie 1 (just removed) eligible
        searched = [i for batch in radarr.searched for i in batch]
        assert 2 not in searched
        assert metrics.registry.get_sample_value(
            "warden_stale_removed_total", {"source": "radarr", "reason": "stalled"}) == 1

    async def test_mass_unhealthy_queue_bails_and_still_excludes(self, make):
        # 3 stalled of 3 = 100% > 50% guard -> remove nothing, but all still excluded from hunt
        stale = [QueueItem(id=10 + i, remote_id=i, title="s", status="warning",
                           error_message="stalled with no connections", added=NOON - timedelta(hours=72))
                 for i in range(3)]
        radarr = FakeArrClient(
            "radarr",
            [missing_item("radarr", i) for i in range(3)] + [missing_item("radarr", 99)],
            arr_type=ArrType.RADARR, queue=stale)
        orch, metrics = make([radarr])
        await orch.tick()
        assert radarr.removed == []                       # bailed
        assert metrics.registry.get_sample_value(
            "warden_stale_sweep_skipped_total", {"source": "radarr"}) == 1
        searched = [i for batch in radarr.searched for i in batch]
        assert all(i not in searched for i in range(3))   # queued ids still excluded
        assert 99 in searched                              # the non-queued item is huntable

    async def test_removal_failure_is_swallowed_and_item_stays_excluded(self, make):
        radarr = FakeArrClient(
            "radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR, remove_raises=True,
            queue=[QueueItem(id=11, remote_id=1, title="s", status="warning",
                             error_message="stalled with no connections", added=NOON - timedelta(hours=72))])
        orch, _ = make([radarr])
        await orch.tick()  # remove raises -> swallowed, no crash
        searched = [i for batch in radarr.searched for i in batch]
        assert 1 not in searched   # removal failed -> still queued -> stays excluded

    async def test_sweep_runs_even_when_source_is_quota_blocked(self, make, repo):
        radarr = FakeArrClient(
            "radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR,
            queue=[QueueItem(id=11, remote_id=1, title="s", status="warning",
                             error_message="stalled with no connections", added=NOON - timedelta(hours=72))])
        qs = StubQuotaSource({ArrType.RADARR: 100})
        orch, _ = make([radarr], quota_source=qs)
        repo.add(f"radarr:{ResetSchedule('00:00').window_key(NOON)}", 80)  # exhaust budget -> blocked
        decision = await orch.tick()
        assert decision.reason == "blocked"
        assert radarr.removed == [11]   # sweep still removed the stale item
        assert radarr.searched == []    # but no hunt (blocked)
