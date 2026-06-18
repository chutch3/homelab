from collections.abc import Callable
from datetime import datetime, timezone

import pytest

from warden.schedule import ResetSchedule
from warden.services.quota import QuotaLedger


def fixed(hour: int) -> datetime:
    return datetime(2026, 6, 16, hour, 0, tzinfo=timezone.utc)


class TestQuotaLedger:
    @pytest.fixture()
    def make(self) -> Callable[[float, int], QuotaLedger]:
        def _make(reserve_pct: float, fallback_budget: int) -> QuotaLedger:
            return QuotaLedger(
                reserve_pct=reserve_pct,
                fallback_budget=fallback_budget,
                schedule=ResetSchedule("00:00"),
            )

        return _make

    def test_budget_applies_reserve(self, make: Callable[[float, int], QuotaLedger]):
        state = make(20, 200).state(spent_today=0, now=fixed(6))
        assert state.daily_budget == 160       # 200 * (1 - 0.20)
        assert state.remaining == 160
        assert state.blocked is False

    def test_remaining_subtracts_spend(self, make: Callable[[float, int], QuotaLedger]):
        state = make(0, 100).state(spent_today=30, now=fixed(6))
        assert state.remaining == 70

    def test_blocked_when_spend_exceeds_budget(self, make: Callable[[float, int], QuotaLedger]):
        state = make(0, 100).state(spent_today=100, now=fixed(6))
        assert state.remaining == 0
        assert state.blocked is True

    def test_reset_at_is_next_local_reset(self, make: Callable[[float, int], QuotaLedger]):
        state = make(0, 100).state(spent_today=0, now=fixed(6))
        assert state.reset_at == datetime(2026, 6, 17, 0, 0, tzinfo=timezone.utc)

    def test_over_spend_clamps_remaining_to_zero_and_blocks(self, make: Callable[[float, int], QuotaLedger]):
        state = make(0, 100).state(spent_today=101, now=fixed(6))
        assert state.remaining == 0
        assert state.blocked is True

    def test_full_reserve_yields_zero_budget(self, make: Callable[[float, int], QuotaLedger]):
        state = make(100, 200).state(spent_today=0, now=fixed(6))
        assert state.daily_budget == 0
        assert state.remaining == 0
        assert state.blocked is True

    def test_explicit_gross_limit_overrides_fallback(self, make: "Callable[[float, int], QuotaLedger]"):
        # fallback budget is 999 but gross_limit=100 with 20% reserve -> 80
        ledger = make(20, 999)
        state = ledger.state(spent_today=0, now=fixed(6), gross_limit=100)
        assert state.daily_budget == 80
        assert state.remaining == 80

    def test_gross_limit_zero_blocks(self, make: "Callable[[float, int], QuotaLedger]"):
        state = make(20, 999).state(spent_today=0, now=fixed(6), gross_limit=0)
        assert state.daily_budget == 0
        assert state.blocked is True
