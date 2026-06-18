from __future__ import annotations

from warden.clock import SystemClock
from warden.logger import get_logger
from warden.metrics import Metrics
from warden.models import ArrClientProtocol, InstanceWanted, QuotaSource, SleepDecision
from warden.repositories.ledger import SearchLedgerRepository
from warden.schedule import ResetSchedule
from warden.services.pacer import Pacer
from warden.services.planner import HuntPlanner
from warden.services.quota import QuotaLedger

_logger = get_logger("warden.orchestrator")


class TickOrchestrator:
    def __init__(
        self,
        clients: list[ArrClientProtocol],
        quota: QuotaLedger,
        pacer: Pacer,
        planner: HuntPlanner,
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
            all_blocked = True
            for client in self._clients:
                src = client.name
                sq = quotas.get(client.arr_type)
                if sq is not None:
                    gross, is_prowlarr, total, defaulted = sq.gross_limit, 1, sq.indexers_total, sq.indexers_defaulted
                else:
                    gross, is_prowlarr, total, defaulted = self._fallback_per_day, 0, 0, 0
                window = f"{src}:{day}"
                spent = self._ledger.spent(window)
                state = self._quota.state(spent_today=spent, now=now, gross_limit=gross)
                m.daily_budget.labels(source=src).set(state.daily_budget)
                m.quota_remaining.labels(source=src).set(state.remaining)
                m.binding_query_limit.labels(source=src).set(gross)
                m.quota_prowlarr.labels(source=src).set(is_prowlarr)
                m.indexers_total.labels(source=src).set(total)
                m.indexers_defaulted.labels(source=src).set(defaulted)
                if state.blocked:
                    m.blocked.labels(source=src).set(1)
                    m.paused_ticks.labels(source=src).inc()
                    _logger.info("source quota-blocked", extra={"event": "blocked", "source": src, "budget": state.daily_budget, "spent": spent, "mode": "prowlarr" if is_prowlarr else "fallback"})
                    continue
                m.blocked.labels(source=src).set(0)
                all_blocked = False
                allowance = self._pacer.allowance(state.remaining, seconds_to_reset)
                issued = await self._hunt_one(client, allowance, window)
                log = _logger.info if issued else _logger.debug
                log("hunt tick", extra={"event": "issued", "source": src, "issued": issued,
                    "allowance": allowance, "remaining": state.remaining, "budget": state.daily_budget,
                    "mode": "prowlarr" if is_prowlarr else "fallback"})

            m.last_tick.set(now.timestamp())
            if all_blocked and self._clients:
                return SleepDecision(seconds=max(0.0, seconds_to_reset), reason="blocked")
            return SleepDecision(seconds=self._poll, reason="paced")

    async def _hunt_one(self, client: ArrClientProtocol, allowance: int, window: str) -> int:
        try:
            missing = await client.list_missing()
            cutoff = await client.list_cutoff_unmet() if self._include_cutoff else []
        except Exception as exc:  # noqa: BLE001 - degrade per-instance
            self._metrics.instance_up.labels(source=client.name).set(0)
            _logger.warning("instance unreachable", extra={"event": "instance_unreachable", "source": client.name, "error": str(exc)})
            return 0
        self._metrics.instance_up.labels(source=client.name).set(1)
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
