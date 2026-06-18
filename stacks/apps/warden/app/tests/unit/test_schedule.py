from datetime import datetime, timezone

import pytest

from warden.schedule import ResetSchedule


def at(hour: int, minute: int = 0, day: int = 16) -> datetime:
    return datetime(2026, 6, day, hour, minute, tzinfo=timezone.utc)


class TestResetSchedule:
    @pytest.fixture()
    def subject(self) -> ResetSchedule:
        return ResetSchedule("01:00")

    def test_window_key_before_reset_uses_previous_day(self, subject: ResetSchedule):
        assert subject.window_key(at(0, 30)) == "2026-06-15"

    def test_window_key_after_reset_uses_current_day(self, subject: ResetSchedule):
        assert subject.window_key(at(2, 0)) == "2026-06-16"

    def test_window_key_on_reset_moment_uses_current_day(self, subject: ResetSchedule):
        assert subject.window_key(at(1, 0)) == "2026-06-16"

    def test_next_reset_is_today_when_before(self, subject: ResetSchedule):
        assert subject.next_reset(at(0, 30)) == at(1, 0)

    def test_next_reset_rolls_to_tomorrow_when_after(self, subject: ResetSchedule):
        assert subject.next_reset(at(2, 0)) == datetime(2026, 6, 17, 1, 0, tzinfo=timezone.utc)

    def test_next_reset_rolls_when_on_boundary(self, subject: ResetSchedule):
        assert subject.next_reset(at(1, 0)) == datetime(2026, 6, 17, 1, 0, tzinfo=timezone.utc)

    def test_window_key_uses_configured_timezone(self):
        # 03:00 UTC = 23:00 (2026-06-15) in New York (EDT) -> previous day's window
        sched = ResetSchedule("00:00", tz="America/New_York")
        now = datetime(2026, 6, 16, 3, 0, tzinfo=timezone.utc)
        assert sched.window_key(now) == "2026-06-15"

    def test_next_reset_in_configured_timezone(self):
        sched = ResetSchedule("00:00", tz="America/New_York")
        now = datetime(2026, 6, 16, 3, 0, tzinfo=timezone.utc)  # 23:00 EDT 06-15
        # next local midnight = 2026-06-16 00:00 EDT = 04:00 UTC
        assert sched.next_reset(now).astimezone(timezone.utc) == datetime(2026, 6, 16, 4, 0, tzinfo=timezone.utc)

    def test_invalid_tz_falls_back_to_utc(self):
        sched = ResetSchedule("00:00", tz="Not/AZone")
        now = datetime(2026, 6, 16, 3, 0, tzinfo=timezone.utc)
        assert sched.window_key(now) == "2026-06-16"
