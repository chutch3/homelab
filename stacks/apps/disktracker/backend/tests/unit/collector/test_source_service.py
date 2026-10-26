"""What the source service decides: when a source is due and in what order, and how a source is
shown. Its repository is its own port, stood in for by a fake. Trying a source is the preview
service's (test_preview_service.py); what is waiting to run, the run service's
(test_run_service.py)."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

import pytest

from disktracker.collector.schemas import ShopifySourceInput
from disktracker.collector.source_repository import Sourced, SourceRepository
from disktracker.collector.source_service import SourceService, due_at, source_key
from tests.unit.fakes import FakeTransactions, FixedClock

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)


def kept(name: str, **fields: Any) -> dict[str, Any]:
    """A source as the repository keeps it: switched on, collected at 03:00, never asked to run
    or stop."""
    return {
        "id": UUID(int=len(name)),
        "key": name.lower(),
        "name": name,
        "kind": "shopify",
        "settings": {"collections": ["hard-drives"], "free_shipping": False},
        "base_url": "https://store.test",
        "schedule": "0 3 * * *",
        "enabled": True,
        "transport": "direct",
        "basis": "unconfirmed",
        "obey_robots": True,
        "notes": "",
        "run_requested_at": None,
        "stop_requested_at": None,
        **fields,
    }


class TestDueAt:
    def test_a_source_that_has_never_run_is_due_now(self) -> None:
        assert due_at(kept("A"), None, NOW) == NOW

    def test_one_that_has_run_is_due_when_its_schedule_first_fires_after_that_run(self) -> None:
        assert due_at(kept("A"), datetime(2026, 9, 20, 3, 5, tzinfo=UTC), NOW) == datetime(
            2026, 9, 21, 3, tzinfo=UTC
        )

    def test_a_store_entered_by_hand_is_never_due_even_when_asked(self) -> None:
        assert due_at(kept("A", kind="manual", run_requested_at=NOW), None, NOW) is None

    def test_a_switched_off_source_is_due_only_when_asked_to_run(self) -> None:
        asked = NOW - timedelta(minutes=5)

        assert due_at(kept("A", enabled=False), None, NOW) is None
        assert due_at(kept("A", enabled=False, run_requested_at=asked), None, NOW) == asked

    def test_a_request_is_answered_by_a_run_that_starts_after_it_not_before(self) -> None:
        asked = NOW - timedelta(hours=1)
        source = kept("A", enabled=False, run_requested_at=asked)

        assert due_at(source, asked - timedelta(minutes=1), NOW) == asked
        assert due_at(source, asked + timedelta(minutes=1), NOW) is None

    def test_a_request_answered_leaves_a_switched_on_source_to_its_schedule(self) -> None:
        asked, ran = NOW - timedelta(hours=1), NOW - timedelta(minutes=30)

        assert due_at(kept("A", run_requested_at=asked), ran, NOW) == datetime(
            2026, 9, 23, 3, tzinfo=UTC
        )


class FakeSources:
    """Holds the sources it is given, each with when its last run started."""

    def __init__(self, *sources: Sourced) -> None:
        self.kept = list(sources)
        self.added: list[dict[str, Any]] = []

    def all(self, by_name: bool = False) -> list[Sourced]:
        return sorted(self.kept, key=lambda s: s[0]["name"]) if by_name else self.kept

    def add(self, values: dict[str, Any]) -> Sourced:
        self.added.append(values)
        return {
            "id": UUID(int=7),
            **values,
            "run_requested_at": None,
            "stop_requested_at": None,
        }, None


def service(sources: FakeSources) -> SourceService:
    return SourceService(FakeTransactions(), cast(SourceRepository, sources), clock=FixedClock(NOW))


class TestDue:
    def test_those_asked_to_run_go_first_in_the_order_asked_then_the_most_overdue(
        self,
    ) -> None:
        ran = NOW - timedelta(hours=1)
        sources = FakeSources(
            (kept("Due Today"), NOW - timedelta(days=1)),
            (kept("Asked Second", run_requested_at=NOW - timedelta(minutes=1)), ran),
            (kept("Overdue"), NOW - timedelta(days=3)),
            (kept("Asked First", run_requested_at=NOW - timedelta(minutes=2)), ran),
            (kept("Never Run"), None),
        )

        due = service(sources).due()

        assert [source["name"] for source in due] == [
            "Asked First", "Asked Second", "Overdue", "Due Today", "Never Run",
        ]  # fmt: skip

    def test_a_source_not_yet_due_or_never_due_is_left_out(self) -> None:
        sources = FakeSources(
            (kept("Ran Today"), NOW - timedelta(hours=1)),
            (kept("Off", enabled=False), None),
            (kept("By Hand", kind="manual"), None),
        )

        assert service(sources).due() == []


class TestSourcesShown:
    def test_a_source_is_shown_with_when_it_is_next_due_and_not_what_it_was_asked(
        self,
    ) -> None:
        asked = NOW - timedelta(minutes=5)
        sources = FakeSources(
            (kept("Off", enabled=False, run_requested_at=asked, stop_requested_at=asked), NOW)
        )

        [shown] = service(sources).listed()

        assert shown == {
            **{k: v for k, v in kept("Off", enabled=False).items()
               if k not in ("run_requested_at", "stop_requested_at")},
            "id": str(UUID(int=3)),
            "next_run_at": None,
        }  # fmt: skip

    def test_a_source_is_shown_without_settings_its_kind_has_since_dropped(self) -> None:
        saved = {"collections": ["all"], "placeholder_price": "100.00"}
        sources = FakeSources((kept("Old", settings=saved), None))

        [shown] = service(sources).listed()

        assert shown["settings"] == {"collections": ["all"]}

    def test_a_new_source_is_kept_under_a_key_made_from_its_name(self) -> None:
        sources = FakeSources()
        entry = ShopifySourceInput.model_validate(
            {"name": "Server Orbit!", "kind": "shopify", "base_url": "https://orbit.test",
             "settings": {"collections": ["all"]}}
        )  # fmt: skip

        added = service(sources).add(entry)

        [values] = sources.added
        assert values["key"] == "serverorbit"
        assert added["next_run_at"] == NOW


@pytest.mark.parametrize(
    ("name", "key"),
    [("ServerPartDeals", "serverpartdeals"), ("Server Orbit", "serverorbit"), ("B&H 2", "bh2")],
)
def test_a_sources_key_is_its_names_letters_and_digits_in_lower_case(name: str, key: str) -> None:
    assert source_key(name) == key
