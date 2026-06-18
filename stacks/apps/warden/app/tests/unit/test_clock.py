from datetime import timezone

import pytest

from warden.clock import SystemClock


class TestSystemClock:
    @pytest.fixture()
    def subject(self) -> SystemClock:
        return SystemClock()

    def test_now_is_timezone_aware_utc(self, subject: SystemClock):
        assert subject.now().tzinfo == timezone.utc
