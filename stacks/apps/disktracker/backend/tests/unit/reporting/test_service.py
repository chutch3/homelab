"""When the reporting service answers a trend from the one it kept, and when it works it out again
and keeps that. Its repository is its own port, stood in for by a fake that keeps one trend and
says the revision of what trends read."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from zoneinfo import ZoneInfo

import pytest

from disktracker.catalog.schemas import DriveScope
from disktracker.reporting.repository import Changes, Kept, ReportingRepository
from disktracker.reporting.service import ReportingService
from tests.unit.fakes import FakeTransactions, FixedClock

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)
KEPT_BODY: dict[str, Any] = {"days": 30, "by": None, "market": {"counted": 99}, "parts": []}


class FakeRepository:
    """Keeps one trend, worked out at revision 1 earlier today; what trends read is at the
    revision the test says."""

    def __init__(self, revision: int = 1, as_of: datetime = NOW) -> None:
        self.trend: dict[str, Any] | None = {"as_of": as_of, "revision": 1, "body": KEPT_BODY}
        self.revision = revision
        self.kept: list[tuple[Any, ...]] = []
        self.asked: list[Any] = []

    def kept_trend(self, days: int, by: str | None, recent_days: int, scope: str) -> Kept:
        self.asked.append(scope)
        return Kept(self.trend, self.revision)

    def price_changes(self, scope: DriveScope) -> Changes:
        self.asked.append(scope)
        return Changes([], self.revision)

    def keep_trend(self, *kept: Any) -> None:
        self.kept.append(kept)


def answered(
    repository: FakeRepository,
    scope: DriveScope | None = None,
    transactions: FakeTransactions | None = None,
) -> dict[str, Any]:
    service = ReportingService(
        transactions or FakeTransactions(), cast(ReportingRepository, repository), FixedClock(NOW)
    )
    return service.trends(30, None, 7, scope or DriveScope())


def test_a_trend_kept_today_from_the_prices_as_they_stand_is_answered_as_it_was_kept() -> None:
    repository, transactions = FakeRepository(), FakeTransactions()

    assert answered(repository, transactions=transactions) is KEPT_BODY
    assert repository.kept == []
    assert transactions.ended == ["read"]


def test_a_trend_kept_in_another_zones_today_is_still_todays() -> None:
    """Days are UTC days, whatever zone the database gave the time it was kept in: kept at 01:00
    UTC, the evening before in New York, it is today's."""
    early = datetime(2026, 9, 22, 1, tzinfo=UTC).astimezone(ZoneInfo("America/New_York"))

    assert early.date() < NOW.date()
    assert answered(FakeRepository(as_of=early)) is KEPT_BODY


@pytest.mark.parametrize(
    "repository",
    [
        FakeRepository(revision=2),
        FakeRepository(as_of=NOW - timedelta(days=1)),
    ],
    ids=["anything it reads changed since", "kept on an earlier day"],
)
def test_otherwise_it_is_worked_out_again_and_kept_under_what_it_was_worked_out_from(
    repository: FakeRepository,
) -> None:
    body = answered(repository)

    assert body["market"]["counted"] == 0
    assert repository.kept == [(30, None, 7, "", body, NOW, repository.revision)]


def test_with_none_kept_it_is_worked_out_and_kept() -> None:
    repository, transactions = FakeRepository(), FakeTransactions()
    repository.trend = None

    body = answered(repository, transactions=transactions)

    assert repository.kept == [(30, None, 7, "", body, NOW, 1)]
    # Read as of one moment, then kept apart from the read.
    assert transactions.ended == ["read", "kept"]


def test_a_trend_of_some_drives_is_read_for_them_and_kept_apart_under_what_narrows_them() -> None:
    repository = FakeRepository()
    repository.trend = None
    scope = DriveScope(capacity=[18000], q="exos")

    answered(repository, scope)

    key = '{"capacity": [18000], "q": "exos"}'
    assert repository.asked == [key, scope]
    assert [kept[3] for kept in repository.kept] == [key]


@pytest.mark.parametrize(
    "scope",
    [
        DriveScope(brand=["Toshiba", "Seagate"], store=["goharddrive", "serverpartdeals"]),
        DriveScope(
            brand=["Seagate", "Toshiba", "Seagate"], store=["serverpartdeals", "goharddrive"]
        ),
    ],
    ids=["one order", "another order, and a choice twice"],
)
def test_the_same_drives_chosen_in_any_order_are_one_kept_trend(scope: DriveScope) -> None:
    """Choices within a filter are ORed: their order and repeats narrow nothing. The words
    searched for are kept as they are."""
    repository = FakeRepository()
    repository.trend = None

    answered(repository, scope)

    assert repository.asked[0] == (
        '{"brand": ["Seagate", "Toshiba"], "store": ["goharddrive", "serverpartdeals"]}'
    )
