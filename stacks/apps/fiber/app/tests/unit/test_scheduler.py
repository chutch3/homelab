from datetime import datetime, timedelta, timezone
from fiber.models import DumpJob, DumpFormat, Engine
from fiber.scheduler import due_jobs
from tests.factories import DumpJobFactory


def _job(service: str, schedule: str = "0 3 * * *") -> DumpJob:
    return DumpJobFactory.build(service=service, host=service, schedule=schedule)


UTC = timezone.utc


def test_due_when_past_fire_and_never_run() -> None:
    now = datetime(2026, 6, 15, 3, 0, 30, tzinfo=UTC)  # just after 03:00
    result = due_jobs([_job("a")], now=now, last_success={}, running=set())
    assert [j.service for j in result] == ["a"]


def test_not_due_when_already_dumped_after_fire() -> None:
    now = datetime(2026, 6, 15, 3, 0, 30, tzinfo=UTC)
    last = {"a": datetime(2026, 6, 15, 3, 0, 5, tzinfo=UTC)}
    assert due_jobs([_job("a")], now=now, last_success=last, running=set()) == []


def test_catch_up_after_downtime() -> None:
    now = datetime(2026, 6, 15, 9, 0, 0, tzinfo=UTC)  # hours after 03:00 fire
    last = {"a": datetime(2026, 6, 14, 3, 0, 5, tzinfo=UTC)}  # yesterday
    assert [j.service for j in due_jobs([_job("a")], now=now, last_success=last, running=set())] == ["a"]


def test_running_job_is_skipped() -> None:
    now = datetime(2026, 6, 15, 3, 0, 30, tzinfo=UTC)
    assert due_jobs([_job("a")], now=now, last_success={}, running={"a"}) == []
