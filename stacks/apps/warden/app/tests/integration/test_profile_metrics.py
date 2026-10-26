from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry

from warden.metrics import Metrics


pytestmark = pytest.mark.integration


class TestProfileMetrics:
    @pytest.fixture()
    def subject(self) -> Metrics:
        return Metrics(CollectorRegistry())

    def test_failure_preserves_last_known_drift_and_freshness(self, subject: Metrics) -> None:
        subject.profile_enabled("radarr", True, 900, 10)
        subject.profile_checked("radarr", {"profile": 2, "custom_format": 1}, 1, 20)
        subject.profile_failed("radarr")
        registry = subject.registry
        assert registry.get_sample_value("warden_profiles_check_success", {"source": "radarr"}) == 0
        assert registry.get_sample_value("warden_profiles_last_successful_check_timestamp_seconds", {"source": "radarr"}) == 20
        assert registry.get_sample_value("warden_profiles_drift_resources", {"source": "radarr", "kind": "profile"}) == 2
        assert registry.get_sample_value("warden_profiles_conflicts", {"source": "radarr"}) == 1
        assert registry.get_sample_value("warden_profiles_drift_since_timestamp_seconds", {"source": "radarr"}) == 20
        subject.profile_checked("radarr", {"profile": 0, "custom_format": 0}, 0, 30)
        assert registry.get_sample_value("warden_profiles_check_success", {"source": "radarr"}) == 1
        assert registry.get_sample_value("warden_profiles_drift_since_timestamp_seconds", {"source": "radarr"}) == 0
        assert registry.get_sample_value("warden_profiles_drift_resources", {"source": "radarr", "kind": "profile"}) == 0

    def test_disabled_source_has_no_stale_baseline(self, subject: Metrics) -> None:
        subject.profile_enabled("sonarr", False, 900, 10)
        registry = subject.registry
        assert registry.get_sample_value("warden_profiles_enabled", {"source": "sonarr"}) == 0
        assert registry.get_sample_value("warden_profiles_last_successful_check_timestamp_seconds", {"source": "sonarr"}) == 0

    def test_persistent_drift_keeps_original_start(self, subject: Metrics) -> None:
        subject.profile_enabled("radarr", True, 30, 10)
        subject.profile_checked("radarr", {"profile": 1, "custom_format": 0}, 0, 20)
        subject.profile_checked("radarr", {"profile": 2, "custom_format": 0}, 0, 50)
        assert subject.registry.get_sample_value("warden_profiles_drift_since_timestamp_seconds", {"source": "radarr"}) == 20
