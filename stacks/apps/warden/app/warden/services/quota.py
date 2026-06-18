from __future__ import annotations

from datetime import datetime
from math import floor

from warden.models import QuotaState
from warden.schedule import ResetSchedule


class QuotaLedger:
    """Computes the daily search budget and remaining headroom (fallback mode).

    The next reset boundary is delegated to the injected ``ResetSchedule`` so the
    window math lives in exactly one place (shared with the orchestrator's window key).
    """

    def __init__(self, reserve_pct: float, fallback_budget: int, schedule: ResetSchedule) -> None:
        self._reserve_pct = reserve_pct
        self._fallback_budget = fallback_budget
        self._schedule = schedule

    def state(self, spent_today: int, now: datetime, gross_limit: int | None = None) -> QuotaState:
        gross = self._fallback_budget if gross_limit is None else gross_limit
        budget = floor(gross * (1 - self._reserve_pct / 100))
        remaining = max(0, budget - spent_today)
        return QuotaState(
            daily_budget=budget,
            spent=spent_today,
            remaining=remaining,
            blocked=remaining <= 0,
            reset_at=self._schedule.next_reset(now),
        )
