from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from fiber.models import MovementOutcome


class Metrics:
    def __init__(self, registry: CollectorRegistry) -> None:
        self.registry = registry
        self.movements = Counter("fiber_movements_total", "Movements by outcome",
                                 ["db", "status"], registry=registry)
        self.last_success = Gauge("fiber_last_success_timestamp", "Last clean dump (unix)",
                                  ["db"], registry=registry)
        self.duration = Histogram("fiber_movement_duration_seconds", "Movement duration",
                                  ["db"], registry=registry)
        self.size = Gauge("fiber_movement_bytes", "Last dump size", ["db"], registry=registry)
        self.in_progress = Gauge("fiber_movement_in_progress", "In-flight movements",
                                 ["db"], registry=registry)
        self.skipped_overlap = Counter("fiber_skipped_overlap_total", "Skipped overlaps",
                                       ["db"], registry=registry)
        self.dingleberries = Counter("fiber_dingleberries_total", "Dingleberries swept",
                                     registry=registry)

    def record_outcome(self, db: str, outcome: MovementOutcome, duration_s: float,
                       nbytes: int, ts: float) -> None:
        self.movements.labels(db=db, status=outcome.value).inc()
        self.duration.labels(db=db).observe(duration_s)
        if outcome is MovementOutcome.CLEAN:
            self.last_success.labels(db=db).set(ts)
            self.size.labels(db=db).set(nbytes)
