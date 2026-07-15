from datetime import datetime, timezone

from fiber.domain.models import MovementOutcome
from fiber.domain.status import DBStatus, derive_status

UTC = timezone.utc


def at(h, m=0) -> datetime:
    return datetime(2026, 6, 15, h, m, tzinfo=UTC)


def test_misconfigured_wins() -> None:
    assert derive_status(
        misconfigured=True,
        running=False,
        last_outcome=None,
        last_success=None,
        schedule="0 3 * * *",
        now=at(9),
    ) is DBStatus.MISCONFIGURED


def test_running_is_straining() -> None:
    assert derive_status(
        misconfigured=False,
        running=True,
        last_outcome=MovementOutcome.CLOGGED,
        last_success=None,
        schedule="0 3 * * *",
        now=at(9),
    ) is DBStatus.STRAINING


def test_last_failed_is_clogged() -> None:
    assert derive_status(
        misconfigured=False,
        running=False,
        last_outcome=MovementOutcome.CLOGGED,
        last_success=at(3),
        schedule="0 3 * * *",
        now=at(4),
    ) is DBStatus.CLOGGED


def test_overdue_is_constipated() -> None:
    # last success was yesterday; 03:00 fired today and no success since
    assert derive_status(
        misconfigured=False,
        running=False,
        last_outcome=MovementOutcome.CLEAN,
        last_success=datetime(2026, 6, 14, 3, tzinfo=UTC),
        schedule="0 3 * * *",
        now=at(9),
    ) is DBStatus.CONSTIPATED


def test_cancelled_recent_is_pinched() -> None:
    assert derive_status(
        misconfigured=False,
        running=False,
        last_outcome=MovementOutcome.PINCHED,
        last_success=at(3),
        schedule="0 3 * * *",
        now=at(4),
    ) is DBStatus.PINCHED


def test_on_schedule_is_clean() -> None:
    assert derive_status(
        misconfigured=False,
        running=False,
        last_outcome=MovementOutcome.CLEAN,
        last_success=at(3),
        schedule="0 3 * * *",
        now=at(4),
    ) is DBStatus.CLEAN
