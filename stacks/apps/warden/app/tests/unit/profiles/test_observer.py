from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from tests.profile_data import REMOTE_FORMAT, REMOTE_PROFILE
from warden.clients.arr import RadarrClient, SonarrClient
from warden.clock import SystemClock
from warden.metrics import Metrics
from warden.profiles.export import export_documents
from warden.profiles.git import GitCatalog, Snapshot
from warden.profiles.observer import Observer


class TestObserver:
    @pytest.fixture()
    def subject(self) -> Observer:
        catalog = Mock(spec=GitCatalog)
        catalog.fetch.return_value = Snapshot("a" * 40, export_documents("radarr", [REMOTE_PROFILE], [REMOTE_FORMAT], ()))
        client = Mock(spec=RadarrClient)
        client.name = "radarr"
        client.list_quality_profiles.return_value = [REMOTE_PROFILE]
        client.list_custom_formats.return_value = [REMOTE_FORMAT]
        clock = Mock(spec=SystemClock)
        clock.now.return_value = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return Observer(catalog, [client], {}, Mock(spec=Metrics), clock, lambda event, fields: None)

    async def test_clean_check_uses_one_snapshot_and_only_reads(self, subject: Observer) -> None:
        await subject.tick()
        subject.catalog.fetch.assert_awaited_once_with()
        subject.clients[0].list_quality_profiles.assert_awaited_once_with()
        subject.clients[0].list_custom_formats.assert_awaited_once_with()
        subject.clients[0].trigger_search.assert_not_called()
        subject.metrics.profile_checked.assert_called_once_with("radarr", {"profile": 0, "custom_format": 0}, 0, 1767225600.0)

    async def test_repository_failure_marks_failure_without_resetting_drift(self, subject: Observer) -> None:
        subject.catalog.fetch.side_effect = ValueError("unreachable")
        await subject.tick()
        subject.metrics.profile_failed.assert_called_once_with("radarr")
        subject.metrics.profile_checked.assert_not_called()
        subject.clients[0].list_quality_profiles.assert_not_called()

    async def test_invalid_target_filter_is_isolated(self, subject: Observer) -> None:
        other = Mock(spec=SonarrClient)
        other.name = "sonarr"
        subject.clients.append(other)
        subject.selections["sonarr"] = "invalid"
        await subject.tick()
        subject.metrics.profile_failed.assert_called_once_with("sonarr")
        subject.metrics.profile_checked.assert_called_once_with("radarr", {"profile": 0, "custom_format": 0}, 0, 1767225600.0)
        other.list_quality_profiles.assert_not_called()

    async def test_disabled_targets_do_not_fetch_or_read(self, subject: Observer) -> None:
        subject.selections["radarr"] = "[]"
        await subject.tick()
        subject.catalog.fetch.assert_not_called()
        subject.clients[0].list_quality_profiles.assert_not_called()

    async def test_counts_resources_not_individual_changed_fields(self, subject: Observer) -> None:
        profile = {**REMOTE_PROFILE, "minFormatScore": 20, "cutoffFormatScore": 500}
        subject.clients[0].list_quality_profiles.return_value = [profile]
        await subject.tick()
        subject.metrics.profile_checked.assert_called_once_with("radarr", {"profile": 1, "custom_format": 0}, 0, 1767225600.0)

    async def test_failed_arr_read_is_not_a_successful_check(self, subject: Observer) -> None:
        subject.clients[0].list_quality_profiles.side_effect = ValueError("failed read")
        await subject.tick()
        subject.metrics.profile_failed.assert_called_once_with("radarr")
        subject.metrics.profile_checked.assert_not_called()
