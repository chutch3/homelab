import pytest
from prometheus_client import CollectorRegistry

from warden import __version__
from warden.metrics import Metrics


class TestMetrics:
    @pytest.fixture()
    def subject(self) -> Metrics:
        return Metrics(CollectorRegistry())

    def test_searches_issued_increments(self, subject: Metrics):
        subject.searches_issued.labels(source="radarr").inc(3)
        assert subject.registry.get_sample_value(
            "warden_searches_issued_total", {"source": "radarr"}) == 3

    def test_quota_gauges_settable(self, subject: Metrics):
        subject.quota_remaining.labels(source="radarr").set(50)
        subject.blocked.labels(source="radarr").set(1)
        assert subject.registry.get_sample_value("warden_quota_remaining", {"source": "radarr"}) == 50
        assert subject.registry.get_sample_value("warden_blocked", {"source": "radarr"}) == 1

    def test_build_info_set_to_version(self, subject: Metrics):
        assert subject.registry.get_sample_value(
            "warden_build_info", {"version": __version__}) == 1

    def test_new_provenance_gauges_settable(self, subject: Metrics):
        subject.binding_query_limit.labels(source="radarr").set(1200)
        subject.quota_prowlarr.labels(source="radarr").set(1)
        subject.indexers_total.labels(source="radarr").set(5)
        subject.indexers_defaulted.labels(source="radarr").set(2)
        subject.paused_ticks.labels(source="radarr").inc(1)
        subject.last_tick.set(1718700000.0)

        assert subject.registry.get_sample_value(
            "warden_binding_query_limit", {"source": "radarr"}) == 1200
        assert subject.registry.get_sample_value(
            "warden_quota_prowlarr", {"source": "radarr"}) == 1
        assert subject.registry.get_sample_value(
            "warden_indexers_total", {"source": "radarr"}) == 5
        assert subject.registry.get_sample_value(
            "warden_indexers_defaulted", {"source": "radarr"}) == 2
        assert subject.registry.get_sample_value(
            "warden_paused_ticks_total", {"source": "radarr"}) == 1
        assert subject.registry.get_sample_value(
            "warden_last_tick_timestamp_seconds", {}) == 1718700000.0


def test_stale_metrics_exist():
    from prometheus_client import CollectorRegistry
    from warden.metrics import Metrics
    m = Metrics(CollectorRegistry())
    m.queue_size.labels(source="radarr").set(3)
    m.queue_stalled.labels(source="radarr").set(1)
    m.stale_removed.labels(source="radarr", reason="stalled").inc()
    m.stale_sweep_skipped.labels(source="radarr").inc()
    reg = m.registry
    assert reg.get_sample_value("warden_queue_size", {"source": "radarr"}) == 3
    assert reg.get_sample_value("warden_stale_removed_total", {"source": "radarr", "reason": "stalled"}) == 1
