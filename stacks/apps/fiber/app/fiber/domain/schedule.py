from __future__ import annotations

from datetime import datetime

from croniter import croniter

from fiber.domain.models import DumpJob


def _previous_fire(schedule: str, now: datetime) -> datetime:
    return croniter(schedule, now).get_prev(datetime)


def next_fire(schedule: str, now: datetime) -> datetime:
    """Return the next scheduled fire time after now."""
    return croniter(schedule, now).get_next(datetime)


def is_overdue(last_success: datetime | None, schedule: str, now: datetime) -> bool:
    return last_success is None or last_success < _previous_fire(schedule, now)


def due_jobs(
    jobs: list[DumpJob],
    now: datetime,
    last_success: dict[str, datetime],
    running: set[str],
) -> list[DumpJob]:
    due: list[DumpJob] = []
    for job in jobs:
        if job.service in running:
            continue
        if is_overdue(last_success.get(job.service), job.schedule, now):
            due.append(job)
    return due
