from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from warden.arr_service import ArrService
from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.profiles.compare import compare_profiles
from warden.profiles.models import ProfileDocument, ProfileSnapshot
from warden.profiles.sources import ProfileSource
from warden.profiles.observer import Observer


class TestObserver:
    @pytest.fixture()
    def subject(self) -> Observer:
        source = Mock(spec=ProfileSource)
        source.fetch.return_value = ProfileSnapshot("a" * 40, (
            ProfileDocument("radarr", "profiles", "hd.yml", {"quality_profiles": [{"name": "HD"}]}),
        ))
        arr = Mock(spec=ArrService)
        arr.sources = ("radarr",)
        arr.get_profiles.return_value = ([{"name": "HD"}], [])
        compare = Mock(spec=compare_profiles)
        compare.return_value = {"changes": [], "conflicts": []}
        clock = Mock(spec=SystemClock)
        clock.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return Observer(source, arr, {}, Mock(spec=Metrics), clock, lambda event, fields: None, compare)

    async def test_tick_clean_check_uses_one_snapshot_and_only_reads(self, subject: Observer) -> None:
        await subject.tick()
        subject.source.fetch.assert_awaited_once_with()
        subject.arr.get_profiles.assert_awaited_once_with("radarr")
        subject.compare.assert_called_once_with("radarr", subject.source.fetch.return_value.documents, [{"name": "HD"}], [], ["HD"])
        subject.metrics.profile_checked.assert_called_once_with("radarr", {"profile": 0, "custom_format": 0}, 0, 1767225600.0)

    async def test_tick_repository_failure_marks_failure_without_resetting_drift(self, subject: Observer) -> None:
        subject.source.fetch.side_effect = ValueError("unreachable")
        await subject.tick()
        subject.metrics.profile_failed.assert_called_once_with("radarr")
        subject.metrics.profile_checked.assert_not_called()
        subject.arr.get_profiles.assert_not_called()

    async def test_tick_invalid_target_filter_is_isolated(self, subject: Observer) -> None:
        subject.arr.sources = ("radarr", "sonarr")
        subject.selections["sonarr"] = "invalid"
        await subject.tick()
        subject.metrics.profile_failed.assert_called_once_with("sonarr")
        subject.metrics.profile_checked.assert_called_once_with("radarr", {"profile": 0, "custom_format": 0}, 0, 1767225600.0)
        subject.arr.get_profiles.assert_awaited_once_with("radarr")

    async def test_tick_disabled_targets_do_not_fetch_or_read(self, subject: Observer) -> None:
        subject.selections["radarr"] = "[]"
        await subject.tick()
        subject.source.fetch.assert_not_called()
        subject.arr.get_profiles.assert_not_called()

    async def test_tick_counts_resources_not_individual_changed_fields(self, subject: Observer) -> None:
        subject.compare.return_value = {"changes": [
            {"kind": "profile", "name": "HD", "field": "min_format_score"},
            {"kind": "profile", "name": "HD", "field": "until_score"},
        ], "conflicts": []}
        await subject.tick()
        subject.metrics.profile_checked.assert_called_once_with("radarr", {"profile": 1, "custom_format": 0}, 0, 1767225600.0)

    async def test_tick_failed_arr_read_is_not_a_successful_check(self, subject: Observer) -> None:
        subject.arr.get_profiles.side_effect = ValueError("failed read")
        await subject.tick()
        subject.metrics.profile_failed.assert_called_once_with("radarr")
        subject.metrics.profile_checked.assert_not_called()
        subject.compare.assert_not_called()
