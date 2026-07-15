from __future__ import annotations

import statistics
from collections.abc import Callable
from datetime import datetime, timezone

from sqlmodel import select

from fiber.db.models import Movement
from fiber.domain.models import Engine, MovementOutcome, MovementRecord


class HistoryRepository:
    def __init__(self, session_factory: Callable) -> None:
        self._session_factory = session_factory

    def record(self, rec: MovementRecord) -> None:
        with self._session_factory() as session:
            movement = Movement(
                service=rec.service,
                engine=rec.engine.value,
                started_at=rec.started_at.isoformat(),
                finished_at=rec.finished_at.isoformat(),
                outcome=rec.outcome.value,
                bytes_written=rec.bytes_written,
                bristol_type=rec.bristol_type,
                sample_path=rec.sample_path,
                receipt_path=rec.receipt_path,
                app_image=rec.app_image,
                app_digest=rec.app_digest,
            )
            session.add(movement)
            session.commit()

    def last_success(self, service: str) -> datetime | None:
        with self._session_factory() as session:
            results = session.exec(
                select(Movement)
                .where(Movement.service == service)
                .where(Movement.outcome == MovementOutcome.CLEAN.value)
            ).all()
        if not results:
            return None
        latest = max(results, key=lambda m: m.finished_at)
        return datetime.fromisoformat(latest.finished_at).astimezone(timezone.utc)

    def median_bytes(self, service: str, limit: int) -> int | None:
        with self._session_factory() as session:
            results = session.exec(
                select(Movement)
                .where(Movement.service == service)
                .where(Movement.outcome == MovementOutcome.CLEAN.value)
                .order_by(Movement.finished_at.desc())  # type: ignore[union-attr]
                .limit(limit)
            ).all()
        if not results:
            return None
        return int(statistics.median(m.bytes_written for m in results))

    def last_outcome(self, service: str) -> MovementOutcome | None:
        with self._session_factory() as session:
            results = session.exec(
                select(Movement)
                .where(Movement.service == service)
                .order_by(Movement.finished_at.desc())  # type: ignore[union-attr]
                .limit(1)
            ).all()
        if not results:
            return None
        return MovementOutcome(results[0].outcome)

    def latest_clean(self, service: str) -> MovementRecord | None:
        with self._session_factory() as session:
            results = session.exec(
                select(Movement)
                .where(Movement.service == service)
                .where(Movement.outcome == MovementOutcome.CLEAN.value)
                .order_by(Movement.finished_at.desc())  # type: ignore[union-attr]
                .limit(1)
            ).all()
        if not results:
            return None
        r = results[0]
        return MovementRecord(
            service=r.service,
            engine=Engine(r.engine),
            started_at=datetime.fromisoformat(r.started_at).astimezone(timezone.utc),
            finished_at=datetime.fromisoformat(r.finished_at).astimezone(timezone.utc),
            outcome=MovementOutcome(r.outcome),
            bytes_written=r.bytes_written,
            bristol_type=r.bristol_type,
            sample_path=r.sample_path,
            receipt_path=r.receipt_path,
            app_image=r.app_image,
            app_digest=r.app_digest,
        )

    def recent(self, service: str, limit: int) -> list[MovementRecord]:
        with self._session_factory() as session:
            results = session.exec(
                select(Movement)
                .where(Movement.service == service)
                .order_by(Movement.finished_at.desc())  # type: ignore[union-attr]
                .limit(limit)
            ).all()
        return [
            MovementRecord(
                service=r.service,
                engine=Engine(r.engine),
                started_at=datetime.fromisoformat(r.started_at).astimezone(timezone.utc),
                finished_at=datetime.fromisoformat(r.finished_at).astimezone(timezone.utc),
                outcome=MovementOutcome(r.outcome),
                bytes_written=r.bytes_written,
                bristol_type=r.bristol_type,
                sample_path=r.sample_path,
                receipt_path=r.receipt_path,
                app_image=r.app_image,
                app_digest=r.app_digest,
            )
            for r in results
        ]
