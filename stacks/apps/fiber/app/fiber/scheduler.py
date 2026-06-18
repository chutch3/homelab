from __future__ import annotations

from datetime import datetime

from croniter import croniter

from fiber.models import DumpJob


def _previous_fire(schedule: str, now: datetime) -> datetime:
    return croniter(schedule, now).get_prev(datetime)


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
        fire = _previous_fire(job.schedule, now)
        last = last_success.get(job.service)
        if last is None or last < fire:
            due.append(job)
    return due
