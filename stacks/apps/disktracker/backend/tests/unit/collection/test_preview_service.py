"""What a source is asked to read when it is tried, and how what it reads is judged. The
collector, the condition rules and the drives are the service's ports, stood in for by fakes."""

from typing import Any, cast

from pydantic import TypeAdapter

from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.drive_service import DriveService
from disktracker.collection.client import CollectorClient
from disktracker.collection.preview_service import PreviewService
from disktracker.collection.schemas import PagePreview, SourcePreviewInput


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


def service(collector: FakeCollector, drives: FakeDrives | None = None) -> PreviewService:
    return PreviewService(
        cast(ConditionRuleService, FakeRules()),
        cast(DriveService, drives or FakeDrives()),
        cast(CollectorClient, collector),
    )


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

        preview = service(collector).preview_source(source)

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

        preview = service(collector, drives).preview_source(source)

        assert preview["verdict"] == {"outcome": "review", "reason": "capacity_conflict"}
