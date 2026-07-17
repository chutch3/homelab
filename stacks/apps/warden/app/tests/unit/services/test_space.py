from collections.abc import Callable

import pytest

from warden.models import RootFolder
from warden.services.space import SpaceGuard, SpaceVerdict

GB = 1_000_000_000


class TestSpaceGuard:
    @pytest.fixture()
    def make(self) -> Callable[[int], SpaceGuard]:
        return lambda min_gb: SpaceGuard(min_free_bytes=min_gb * GB)

    def test_disabled_when_floor_is_zero(self, make):
        assert make(0).enabled is False

    def test_enabled_when_floor_is_positive(self, make):
        assert make(50).enabled is True

    def test_no_readings_returns_none_so_caller_fails_open(self, make):
        assert make(50).evaluate([], committed_bytes=0) is None

    def test_blocks_when_free_below_floor(self, make):
        verdict = make(50).evaluate([RootFolder("/data", 5 * GB)], committed_bytes=0)
        assert verdict == SpaceVerdict(blocked=True, free_bytes=5 * GB, projected_bytes=5 * GB,
                                       path="/data")

    def test_allows_when_free_at_or_above_floor(self, make):
        # exactly at the floor is allowed (block is strictly-below)
        verdict = make(50).evaluate([RootFolder("/data", 50 * GB)], committed_bytes=0)
        assert verdict.blocked is False
        assert verdict.projected_bytes == 50 * GB

    def test_uses_smallest_free_space_across_root_folders(self, make):
        verdict = make(50).evaluate(
            [RootFolder("/a", 500 * GB), RootFolder("/b", 10 * GB)], committed_bytes=0)
        assert verdict.blocked is True
        assert verdict.free_bytes == 10 * GB
        assert verdict.path == "/b"          # verdict identifies the tightest folder

    def test_in_flight_queue_subtracts_from_headroom(self, make):
        # 100 GB free clears the 50 GB floor, but 80 GB still downloading pushes projected
        # headroom to 20 GB -> blocked.
        verdict = make(50).evaluate([RootFolder("/data", 100 * GB)], committed_bytes=80 * GB)
        assert verdict.blocked is True
        assert verdict.free_bytes == 100 * GB
        assert verdict.projected_bytes == 20 * GB

    def test_projected_headroom_can_go_negative(self, make):
        verdict = make(10).evaluate([RootFolder("/data", 5 * GB)], committed_bytes=8 * GB)
        assert verdict.blocked is True
        assert verdict.projected_bytes == -3 * GB
