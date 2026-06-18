from __future__ import annotations

import pytest
from prometheus_client import CollectorRegistry

from fiber.metrics import Metrics
from fiber.models import MovementOutcome


class TestMetrics:
    @pytest.fixture()
    def subject(self) -> Metrics:
        return Metrics(registry=CollectorRegistry())

    def test_records_outcome_and_last_success(self, subject: Metrics) -> None:
        subject.record_outcome("kenku-pg", MovementOutcome.CLEAN, duration_s=12.0, nbytes=2048, ts=1000.0)
        registry = subject.registry
        assert registry.get_sample_value("fiber_movements_total", {"db": "kenku-pg", "status": "clean"}) == 1.0
        assert registry.get_sample_value("fiber_last_success_timestamp", {"db": "kenku-pg"}) == 1000.0
        assert registry.get_sample_value("fiber_movement_bytes", {"db": "kenku-pg"}) == 2048.0
