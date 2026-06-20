from __future__ import annotations

from datetime import datetime

from warden.clock import SystemClock
from warden.logger import get_logger
from warden.metrics import Metrics
from warden.models import (
    ArrClientProtocol, InstanceWanted, QueueItem, QuotaSource, QuotaState, SleepDecision, WantedItem,
)
from warden.repositories.ledger import SearchLedgerRepository
from warden.repositories.progress import QueueProgressRepository
from warden.schedule import ResetSchedule
from warden.services.pacer import Pacer
from warden.services.planner import HuntPlanner
from warden.services.progress import ProgressTracker
from warden.services.quota import QuotaLedger
from warden.services.stale import StaleVerdict
from warden.services.sweeper import QueueSweeper

_logger = get_logger("warden.orchestrator")


class TickOrchestrator:
    def __init__(
        self,
        clients: list[ArrClientProtocol],
        quota: QuotaLedger,
        pacer: Pacer,
        planner: HuntPlanner,
        sweeper: QueueSweeper,
        tracker: ProgressTracker,
        progress_repo: QueueProgressRepository,
        ledger: SearchLedgerRepository,
        clock: SystemClock,
        metrics: Metrics,
        schedule: ResetSchedule,
        quota_source: QuotaSource,
        include_cutoff_unmet: bool,
        fallback_per_day: int,
        prowlarr_fallback_on_error: bool,
        poll_interval_sec: float,
    ) -> None:
        self._clients = clients
        self._quota = quota
        self._pacer = pacer
        self._planner = planner
        self._sweeper = sweeper
        self._tracker = tracker
        self._progress_repo = progress_repo
        self._ledger = ledger
        self._clock = clock
        self._metrics = metrics
        self._schedule = schedule
        self._quota_source = quota_source
        self._include_cutoff = include_cutoff_unmet
        self._fallback_per_day = fallback_per_day
        self._prowlarr_fallback_on_error = prowlarr_fallback_on_error
        self._poll = poll_interval_sec

    async def tick(self) -> SleepDecision:
        with self._metrics.tick_duration.time():
            now = self._clock.now()
            day = self._schedule.window_key(now)
            reset_at = self._schedule.next_reset(now)
            seconds_to_reset = (reset_at - now).total_seconds()
            try:
                quotas = await self._quota_source.quotas()
                self._metrics.prowlarr_up.set(1)
            except Exception as exc:  # noqa: BLE001 - quota source unreachable
                self._metrics.prowlarr_up.set(0)
                if not self._prowlarr_fallback_on_error:
                    raise
                _logger.warning("quota source unreachable; using fallback", extra={"event": "quota_source_unreachable", "error": str(exc)})
                quotas = {}

            m = self._metrics
            prior_progress = self._progress_repo.snapshot()
            next_progress: dict = {}
            all_blocked = True
            for client in self._clients:
                src = client.name
                try:
                    queue = await client.list_queue()
                    missing = await client.list_missing()
                    cutoff = await client.list_cutoff_unmet() if self._include_cutoff else []
                except Exception as exc:  # noqa: BLE001 - degrade per-instance
                    m.instance_up.labels(source=src).set(0)
                    all_blocked = False  # unreachable -> retry next poll, not a quota sleep
                    _logger.warning("instance unreachable",
                                    extra={"event": "instance_unreachable", "source": src, "error": str(exc)})
                    continue
                m.instance_up.labels(source=src).set(1)
                m.never_searched.labels(source=src).set(
                    sum(1 for w in missing if w.last_search_time is None))

                np_items, client_progress = self._tracker.evaluate(queue, prior_progress, now)
                next_progress.update(client_progress)
                m.queue_no_progress.labels(source=src).set(len(np_items))
                extra = [StaleVerdict(item=i, reason="no_progress") for i in np_items]
                exclusion = await self._sweep(client, queue, now, extra)

                window = f"{src}:{day}"
                state, is_prowlarr, spent = self._publish_quota_state(client, quotas, now, window)
                if state.blocked:
                    m.blocked.labels(source=src).set(1)
                    m.paused_ticks.labels(source=src).inc()
                    _logger.info("source quota-blocked", extra={"event": "blocked", "source": src, "budget": state.daily_budget, "spent": spent, "mode": "prowlarr" if is_prowlarr else "fallback"})
                    continue
                m.blocked.labels(source=src).set(0)
                all_blocked = False
                allowance = self._pacer.allowance(state.remaining, seconds_to_reset)
                issued = await self._hunt_one(client, allowance, window, missing, cutoff, exclusion)
                log = _logger.info if issued else _logger.debug
                log("hunt tick", extra={"event": "issued", "source": src, "issued": issued,
                    "allowance": allowance, "remaining": state.remaining, "budget": state.daily_budget,
                    "mode": "prowlarr" if is_prowlarr else "fallback"})

            self._progress_repo.replace(next_progress)
            m.last_tick.set(now.timestamp())
            if all_blocked and self._clients:
                return SleepDecision(seconds=max(0.0, seconds_to_reset), reason="blocked")
            return SleepDecision(seconds=self._poll, reason="paced")

    def _publish_quota_state(self, client: ArrClientProtocol, quotas: dict, now: datetime,
                             window: str) -> tuple[QuotaState, int, int]:
        """Resolve a source's budget (Prowlarr or flat fallback), publish its quota
        metrics, and return (state, is_prowlarr, spent_today)."""
        m = self._metrics
        src = client.name
        sq = quotas.get(client.arr_type)
        if sq is not None:
            gross, is_prowlarr, total, defaulted = sq.gross_limit, 1, sq.indexers_total, sq.indexers_defaulted
        else:
            gross, is_prowlarr, total, defaulted = self._fallback_per_day, 0, 0, 0
        spent = self._ledger.spent(window)
        state = self._quota.state(spent_today=spent, now=now, gross_limit=gross)
        m.daily_budget.labels(source=src).set(state.daily_budget)
        m.quota_remaining.labels(source=src).set(state.remaining)
        m.binding_query_limit.labels(source=src).set(gross)
        m.quota_prowlarr.labels(source=src).set(is_prowlarr)
        m.indexers_total.labels(source=src).set(total)
        m.indexers_defaulted.labels(source=src).set(defaulted)
        return state, is_prowlarr, spent

    async def _sweep(self, client: ArrClientProtocol, queue: list[QueueItem], now: datetime,
                     extra: list[StaleVerdict]) -> set[int]:
        """Execute the sweep (runs even when the source is quota-blocked) and return the
        hunt-exclusion set (queued remote ids minus those removed this tick)."""
        m = self._metrics
        src = client.name
        decision = self._sweeper.plan(queue, now, extra)
        m.queue_size.labels(source=src).set(decision.queue_size)
        m.queue_stalled.labels(source=src).set(decision.stalled_count)
        removed: set[int] = set()
        if decision.skipped:
            m.stale_sweep_skipped.labels(source=src).inc()
            _logger.warning("stale sweep skipped", extra={"event": "stale_sweep_skipped",
                "source": src, "queue_size": decision.queue_size, "stalled": decision.stalled_count})
        else:
            for act in decision.to_remove:
                try:
                    await client.remove_queue_item(act.queue_id, remove_from_client=True, blocklist=True)
                except Exception:  # noqa: BLE001 - one bad removal shouldn't abort the sweep
                    _logger.exception("stale removal failed", extra={"event": "stale_remove_error",
                        "source": src, "id": act.queue_id})
                    continue
                removed.add(act.remote_id)
                m.stale_removed.labels(source=src, reason=act.reason).inc()
                _logger.info("stale removed", extra={"event": "stale_removed", "source": src,
                    "id": act.queue_id, "reason": act.reason, "age_h": round(act.age_hours, 1)})
        return set(decision.all_queued_remote_ids) - removed

    async def _hunt_one(self, client: ArrClientProtocol, allowance: int, window: str,
                        missing: list[WantedItem], cutoff: list[WantedItem], exclusion: set[int]) -> int:
        missing = [w for w in missing if w.remote_id not in exclusion]
        cutoff = [w for w in cutoff if w.remote_id not in exclusion]
        wanted = {client.name: InstanceWanted(tuple(missing), tuple(cutoff))}
        selected = self._planner.plan(allowance=allowance, wanted=wanted)
        if not selected:
            _logger.info("nothing to hunt", extra={"event": "nothing_to_hunt", "source": client.name,
                "missing": len(missing), "cutoff": len(cutoff)})
            return 0
        for item in selected:
            _logger.info("search triggered", extra={"event": "search_triggered", "source": client.name,
                "arr_type": client.arr_type.value, "id": item.remote_id, "title": item.title,
                "kind": item.kind.value})
        ids = [i.remote_id for i in selected]
        await client.trigger_search(ids)
        self._metrics.searches_issued.labels(source=client.name).inc(len(ids))
        self._ledger.add(window, len(ids))
        return len(ids)
