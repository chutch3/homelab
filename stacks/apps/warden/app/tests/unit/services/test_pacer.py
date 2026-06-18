import pytest

from warden.services.pacer import Pacer


class TestPacer:
    @pytest.fixture()
    def subject(self) -> Pacer:
        return Pacer(poll_interval_sec=300)

    def test_zero_remaining_yields_zero(self, subject: Pacer):
        assert subject.allowance(remaining=0, seconds_to_reset=3600) == 0

    def test_spreads_evenly_across_remaining_ticks(self, subject: Pacer):
        # 1 hour to reset, 300s ticks => 12 ticks; 120 remaining => 10 per tick
        assert subject.allowance(remaining=120, seconds_to_reset=3600) == 10

    def test_caps_at_remaining_when_one_tick_left(self, subject: Pacer):
        # ~1 tick left => floor(3/1)=3, capped at remaining => 3 (never exceeds remaining)
        assert subject.allowance(remaining=3, seconds_to_reset=100) == 3

    def test_at_least_one_when_remaining_positive(self, subject: Pacer):
        # tiny remaining, far from reset => still allow 1 so progress is made
        assert subject.allowance(remaining=1, seconds_to_reset=36000) == 1

    def test_does_not_dump_large_budget_when_ticks_exceed_remaining(self, subject: Pacer):
        # 200 ticks left, only 100 budget => floor(100/200)=0 -> at least 1, NOT 100
        assert subject.allowance(remaining=100, seconds_to_reset=60000) == 1
