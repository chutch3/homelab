"""What the collection service decides: when a source is due and in what order, how a source is
shown, and what the collector is asked when a source is tried. Its repository, the catalog's
queries and the collector client are its own ports, stood in for by fakes."""

from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from pydantic import TypeAdapter

from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.drive_service import DriveService
from disktracker.collection.client import CollectorClient
from disktracker.collection.repository import CollectionRepository, Sourced
from disktracker.collection.schemas import PagePreview, ShopifySourceInput, SourcePreviewInput
from disktracker.collection.service import CollectionService, due_at

NOW = datetime(2026, 9, 22, 12, tzinfo=UTC)
NEW_ID = UUID(int=7)


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


class FakeRepository:
    """Holds the sources it is given, each with when its last run started."""

    def __init__(self, *sources: Sourced) -> None:
        self.kept = list(sources)
        self.running: list[dict[str, Any]] = []
        self.added: list[dict[str, Any]] = []

    def sources(self, by_name: bool = False) -> list[Sourced]:
        return sorted(self.kept, key=lambda s: s[0]["name"]) if by_name else self.kept

    def add_source(self, values: dict[str, Any]) -> Sourced:
        self.added.append(values)
        return {**values, "run_requested_at": None, "stop_requested_at": None}, None

    def collector_status(self) -> tuple[datetime | None, list[dict[str, Any]], list[Sourced]]:
        return None, self.running, self.kept


class FakeRules:
    def all(self) -> list[dict[str, Any]]:
        return [{"pattern": "recertified", "condition": "manufacturer_recertified"}]


class FakeDrives:
    def __init__(self, capacities: dict[str, int] | None = None) -> None:
        self.capacities = capacities or {}

    def capacity(self, mpn: str) -> int | None:
        return self.capacities.get(mpn)


class FakeCollector:
    """Answers a preview as it is set to, and keeps what it was asked."""

    def __init__(self, answer: dict[str, Any]) -> None:
        self.answer = answer
        self.asked: list[dict[str, Any]] = []

    def preview(self, source: dict[str, Any]) -> dict[str, Any]:
        self.asked.append(source)
        return self.answer


def service(
    repository: FakeRepository,
    collector: FakeCollector | None = None,
    drives: FakeDrives | None = None,
) -> CollectionService:
    return CollectionService(
        cast(CollectionRepository, repository),
        cast(ConditionRuleService, FakeRules()),
        cast(DriveService, drives or FakeDrives()),
        cast(CollectorClient, collector),
        now=lambda: NOW,
        next_id=lambda: NEW_ID,
    )


class TestDue:
    def test_those_asked_to_run_go_first_in_the_order_asked_then_the_most_overdue(
        self,
    ) -> None:
        ran = NOW - timedelta(hours=1)
        repository = FakeRepository(
            (kept("Due Today"), NOW - timedelta(days=1)),
            (kept("Asked Second", run_requested_at=NOW - timedelta(minutes=1)), ran),
            (kept("Overdue"), NOW - timedelta(days=3)),
            (kept("Asked First", run_requested_at=NOW - timedelta(minutes=2)), ran),
            (kept("Never Run"), None),
        )

        due = service(repository).due_sources()

        assert [source["name"] for source in due] == [
            "Asked First", "Asked Second", "Overdue", "Due Today", "Never Run",
        ]  # fmt: skip

    def test_a_source_not_yet_due_or_never_due_is_left_out(self) -> None:
        repository = FakeRepository(
            (kept("Ran Today"), NOW - timedelta(hours=1)),
            (kept("Off", enabled=False), None),
            (kept("By Hand", kind="manual"), None),
        )

        assert service(repository).due_sources() == []

    def test_what_is_waiting_leaves_out_sources_already_running(self) -> None:
        repository = FakeRepository((kept("Busy"), None), (kept("Idle"), None))
        repository.running = [{"source": "busy"}]

        assert service(repository).collector_status()["waiting"] == ["idle"]


class TestSourcesShown:
    def test_a_source_is_shown_with_when_it_is_next_due_and_not_what_it_was_asked(
        self,
    ) -> None:
        asked = NOW - timedelta(minutes=5)
        repository = FakeRepository(
            (kept("Off", enabled=False, run_requested_at=asked, stop_requested_at=asked), NOW)
        )

        [shown] = service(repository).list_sources()

        assert shown == {
            **{k: v for k, v in kept("Off", enabled=False).items()
               if k not in ("run_requested_at", "stop_requested_at")},
            "id": str(UUID(int=3)),
            "next_run_at": None,
        }  # fmt: skip

    def test_a_source_is_shown_without_settings_its_kind_has_since_dropped(self) -> None:
        saved = {"collections": ["all"], "placeholder_price": "100.00"}
        repository = FakeRepository((kept("Old", settings=saved), None))

        [shown] = service(repository).list_sources()

        assert shown["settings"] == {"collections": ["all"]}

    def test_a_new_source_is_kept_under_a_key_made_from_its_name(self) -> None:
        repository = FakeRepository()
        entry = ShopifySourceInput.model_validate(
            {"name": "Server Orbit!", "kind": "shopify", "base_url": "https://orbit.test",
             "settings": {"collections": ["all"]}}
        )  # fmt: skip

        added = service(repository).add_source(entry)

        [values] = repository.added
        assert (values["id"], values["key"]) == (NEW_ID, "serverorbit")
        assert added["next_run_at"] == NOW


OFFER = {
    "title": "Seagate Exos X18 ST18000NM000J 20TB",
    "mpn": "ST18000NM000J",
    "condition": "new",
    "capacity_gb": 20000,
    "in_stock": True,
}


class TestPreview:
    def test_the_collector_is_asked_for_the_source_as_it_would_be_saved(self) -> None:
        collector = FakeCollector({"status": "nothing", "reason": None, "offer": None})
        source: PagePreview = TypeAdapter(SourcePreviewInput).validate_python(
            {"name": "Server Orbit!", "kind": "shopify", "base_url": "https://orbit.test",
             "settings": {"collections": ["all"]}}
        )  # fmt: skip

        preview = service(FakeRepository(), collector).preview_source(source)

        assert collector.asked == [
            {
                "key": "serverorbit",
                "kind": "shopify",
                "base_url": "https://orbit.test",
                "transport": "direct",
                "obey_robots": True,
                "settings": {"collections": ["all"], "free_shipping": False},
                "conditions": FakeRules().all(),
                "page_url": None,
            }
        ]
        # Without an offer there is nothing to judge.
        assert preview == {"status": "nothing", "reason": None, "offer": None, "verdict": None}

    def test_an_offer_is_judged_against_the_drive_as_the_catalog_has_it(self) -> None:
        collector = FakeCollector({"status": "found", "reason": None, "offer": OFFER})
        drives = FakeDrives({"ST18000NM000J": 18000})
        source: PagePreview = TypeAdapter(SourcePreviewInput).validate_python(
            {"name": "Orbit", "kind": "shopify", "base_url": "https://orbit.test",
             "settings": {"collections": ["all"]}}
        )  # fmt: skip

        preview = service(FakeRepository(), collector, drives).preview_source(source)

        assert preview["verdict"] == {"outcome": "review", "reason": "capacity_conflict"}
