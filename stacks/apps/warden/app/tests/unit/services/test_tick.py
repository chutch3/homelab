from collections.abc import Callable
from datetime import datetime, timedelta, timezone

import pytest
from prometheus_client import CollectorRegistry

from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.models import ArrType, GrabEvent, QueueItem, SourceQuota
from warden.repositories.ledger import SearchLedgerRepository
from warden.schedule import ResetSchedule
from warden.services.backoff import BackoffTracker
from warden.services.efficacy import EfficacyTracker
from warden.services.orchestrator import TickOrchestrator
from warden.services.pacer import Pacer
from warden.services.planner import HuntPlanner
from warden.services.quota import QuotaLedger
from warden.services.quota_source import FallbackQuotaSource
from warden.services.progress import ProgressTracker
from warden.services.stale import StaleDetector
from warden.services.sweeper import QueueSweeper
from tests.factories import (
    FakeArrClient, make_backoff_repo, make_efficacy_repo, make_progress_repo, missing_item,
    wanted_item,
)


def _sweeper() -> QueueSweeper:
    return QueueSweeper(StaleDetector(grace_hours=48), enabled=True, max_removals_per_tick=5,
                        mass_fraction=0.5, min_queue_for_guard=3)


def _tracker() -> ProgressTracker:
    return ProgressTracker(window_hours=6, min_progress_bytes=100_000_000, enabled=True)


def _efficacy(enabled: bool = True) -> EfficacyTracker:
    return EfficacyTracker(enabled=enabled, resolve_window=timedelta(minutes=30))


def _backoff(enabled: bool = True, threshold: int = 3) -> BackoffTracker:
    return BackoffTracker(enabled=enabled, threshold=threshold, cooldown=timedelta(days=30))


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
                  prowlarr_fallback_on_error=True, progress_repo=None, efficacy_repo=None,
                  efficacy=None, backoff=None, backoff_repo=None):
            schedule = ResetSchedule("00:00")
            metrics = Metrics(CollectorRegistry())
            orch = TickOrchestrator(
                clients=clients,
                quota=QuotaLedger(reserve_pct=reserve, fallback_budget=fallback, schedule=schedule),
                pacer=Pacer(poll_interval_sec=poll),
                planner=HuntPlanner(),
                sweeper=_sweeper(),
                tracker=_tracker(),
                progress_repo=progress_repo or make_progress_repo(),
                efficacy=efficacy or _efficacy(),
                efficacy_repo=efficacy_repo or make_efficacy_repo(),
                backoff=backoff or _backoff(),
                backoff_repo=backoff_repo or make_backoff_repo(),
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

    async def test_all_sources_blocked_keeps_poll_cadence_so_janitor_runs(self, make, repo):
        # when quota-blocked, warden must still wake every poll interval to run the (free)
        # queue janitor — NOT sleep until the daily reset (which would starve the sweep).
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        qs = StubQuotaSource({ArrType.RADARR: 100})
        orch, _ = make([radarr], quota_source=qs, poll=300)
        repo.add(f"radarr:{ResetSchedule('00:00').window_key(NOON)}", 80)
        decision = await orch.tick()
        assert radarr.searched == []
        assert decision.reason == "blocked"
        assert decision.seconds == 300          # poll interval, not seconds_to_reset

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

    async def test_mass_unavailable_queue_bails_and_still_excludes(self, make):
        # >50% downloadClientUnavailable (the outage signal) -> guard bails (no removals),
        # but the queued ids are still excluded from hunting
        unavail = [QueueItem(id=10 + i, remote_id=i, title="u", status="downloadClientUnavailable",
                             error_message="", added=NOON - timedelta(hours=72),
                             download_id="", size_left=0)
                   for i in range(3)]
        radarr = FakeArrClient(
            "radarr",
            [missing_item("radarr", i) for i in range(3)] + [missing_item("radarr", 99)],
            arr_type=ArrType.RADARR, queue=unavail)
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

    async def test_no_progress_download_is_removed(self, make):
        from warden.models import Anchor
        # pre-seed an anchor 7h ago (> 6h window); item still has the same sizeleft -> no progress
        repo = make_progress_repo()
        repo.replace({"DID1": Anchor(1000, NOON - timedelta(hours=7))})
        radarr = FakeArrClient(
            "radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR,
            queue=[QueueItem(id=55, remote_id=1, title="stuck", status="downloading",
                             error_message="", added=NOON - timedelta(hours=30),
                             download_id="DID1", size_left=1000)])
        orch, metrics = make([radarr], progress_repo=repo)
        await orch.tick()
        assert radarr.removed == [55]
        assert metrics.registry.get_sample_value(
            "warden_stale_removed_total", {"source": "radarr", "reason": "no_progress"}) == 1

    async def test_sets_never_searched_metric(self, make):
        radarr = FakeArrClient("radarr", [
            missing_item("radarr", 1),                          # last_search_time None
            missing_item("radarr", 2),                          # None
            wanted_item("radarr", 3, last_search_time=NOON),    # searched
        ], arr_type=ArrType.RADARR)
        orch, metrics = make([radarr])
        await orch.tick()
        assert metrics.registry.get_sample_value(
            "warden_never_searched", {"source": "radarr"}) == 2

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

    async def test_records_search_attempts_for_each_hunted_item(self, make):
        eff = make_efficacy_repo()
        radarr = FakeArrClient("radarr", [missing_item("radarr", 7)], arr_type=ArrType.RADARR)
        orch, metrics = make([radarr], efficacy_repo=eff)
        await orch.tick()
        assert [a.remote_id for a in eff.pending("radarr")] == [7]
        assert metrics.registry.get_sample_value(
            "warden_search_pending", {"source": "radarr"}) == 1

    async def test_grab_for_a_searched_item_counts_as_a_hit(self, make):
        eff = make_efficacy_repo()
        eff.record("radarr", [(7, "missing")], NOON - timedelta(minutes=10))
        radarr = FakeArrClient(
            "radarr", [], arr_type=ArrType.RADARR,
            grabs=[GrabEvent(remote_id=7, indexer="EZTVL", at=NOON - timedelta(minutes=5),
                             release_source="UserInvokedSearch")])
        orch, metrics = make([radarr], efficacy_repo=eff)
        await orch.tick()
        assert metrics.registry.get_sample_value(
            "warden_search_hit_total", {"source": "radarr", "indexer": "EZTVL"}) == 1
        assert eff.pending("radarr") == []           # resolved -> dropped
        assert radarr.grabbed_since == [NOON - timedelta(minutes=10)]   # polled since oldest pending

    async def test_unresolved_attempt_past_window_counts_as_a_miss(self, make):
        eff = make_efficacy_repo()
        eff.record("radarr", [(7, "missing")], NOON - timedelta(minutes=45))   # older than 30m window
        radarr = FakeArrClient("radarr", [], arr_type=ArrType.RADARR, grabs=[])
        orch, metrics = make([radarr], efficacy_repo=eff)
        await orch.tick()
        assert metrics.registry.get_sample_value(
            "warden_search_miss_total", {"source": "radarr"}) == 1
        assert eff.pending("radarr") == []

    async def test_efficacy_reconciles_even_when_blocked(self, make, repo):
        eff = make_efficacy_repo()
        eff.record("radarr", [(7, "missing")], NOON - timedelta(minutes=10))
        radarr = FakeArrClient(
            "radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR,
            grabs=[GrabEvent(remote_id=7, indexer="Knaben", at=NOON - timedelta(minutes=5),
                             release_source="Search")])
        qs = StubQuotaSource({ArrType.RADARR: 100})
        orch, metrics = make([radarr], quota_source=qs, efficacy_repo=eff)
        repo.add(f"radarr:{ResetSchedule('00:00').window_key(NOON)}", 80)   # blocked
        decision = await orch.tick()
        assert decision.reason == "blocked"
        assert metrics.registry.get_sample_value(
            "warden_search_hit_total", {"source": "radarr", "indexer": "Knaben"}) == 1

    async def test_history_error_does_not_abort_the_tick(self, make):
        eff = make_efficacy_repo()
        eff.record("radarr", [(7, "missing")], NOON - timedelta(minutes=10))
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR,
                               grab_raises=True)
        orch, _ = make([radarr], efficacy_repo=eff)
        await orch.tick()
        assert radarr.searched == [[1]]              # hunt still happened
        assert [a.remote_id for a in eff.pending("radarr")] == [1, 7]   # 7 stays pending, 1 newly recorded

    async def test_efficacy_disabled_skips_history_and_recording(self, make):
        eff = make_efficacy_repo()
        radarr = FakeArrClient("radarr", [missing_item("radarr", 1)], arr_type=ArrType.RADARR)
        orch, _ = make([radarr], efficacy_repo=eff, efficacy=_efficacy(enabled=False))
        await orch.tick()
        assert radarr.grabbed_since == []            # never polled history
        assert eff.pending("radarr") == []           # nothing recorded

    async def test_miss_backs_off_item_and_excludes_it_from_hunt(self, make):
        eff = make_efficacy_repo()
        boff = make_backoff_repo()
        eff.record("radarr", [(7, "missing")], NOON - timedelta(minutes=45))   # will miss this tick
        radarr = FakeArrClient("radarr", [missing_item("radarr", 7)], arr_type=ArrType.RADARR, grabs=[])
        orch, metrics = make([radarr], efficacy_repo=eff, backoff_repo=boff,
                             backoff=_backoff(threshold=1))   # one miss is enough to back off
        await orch.tick()
        assert boff.active("radarr", NOON.timestamp()) == {7}
        assert metrics.registry.get_sample_value("warden_backoff_active", {"source": "radarr"}) == 1
        assert metrics.registry.get_sample_value(
            "warden_backoff_entered_total", {"source": "radarr"}) == 1
        searched = [i for batch in radarr.searched for i in batch]
        assert 7 not in searched                      # excluded from hunting same tick

    async def test_hit_clears_backoff(self, make):
        boff = make_backoff_repo()
        boff.write("radarr", clear=frozenset(),
                   upsert={7: (5, (NOON + timedelta(days=1)).timestamp())})   # already backed off
        eff = make_efficacy_repo()
        eff.record("radarr", [(7, "missing")], NOON - timedelta(minutes=10))
        radarr = FakeArrClient(
            "radarr", [], arr_type=ArrType.RADARR,
            grabs=[GrabEvent(remote_id=7, indexer="X", at=NOON - timedelta(minutes=5),
                             release_source="Search")])
        orch, metrics = make([radarr], efficacy_repo=eff, backoff_repo=boff)
        await orch.tick()
        assert boff.streaks("radarr", [7]) == {}      # the grab reset it
        assert metrics.registry.get_sample_value("warden_backoff_active", {"source": "radarr"}) == 0

    async def test_backoff_disabled_does_not_exclude_or_record(self, make):
        boff = make_backoff_repo()
        boff.write("radarr", clear=frozenset(),
                   upsert={7: (9, (NOON + timedelta(days=1)).timestamp())})
        eff = make_efficacy_repo()
        eff.record("radarr", [(8, "missing")], NOON - timedelta(minutes=45))   # a miss reaches _apply_backoff
        radarr = FakeArrClient("radarr", [missing_item("radarr", 7)], arr_type=ArrType.RADARR, grabs=[])
        orch, _ = make([radarr], efficacy_repo=eff, backoff_repo=boff, backoff=_backoff(enabled=False))
        await orch.tick()
        searched = [i for batch in radarr.searched for i in batch]
        assert 7 in searched                          # disabled -> active() not consulted
        assert boff.streaks("radarr", [8]) == {}      # disabled -> no streak recorded for the miss
