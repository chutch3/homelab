"""What a source is asked to read when it is tried, and how what it reads is judged. The
collector, the condition rules and ingestion are the service's ports, stood in for by fakes."""

from typing import Any, cast

from pydantic import TypeAdapter

from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.ingestion_service import CollectedPage, IngestionService
from disktracker.catalog.verdict import Verdict
from disktracker.collector.client import CollectorClient
from disktracker.collector.preview_service import PreviewService
from disktracker.collector.schemas import PagePreview, SourcePreviewInput


class FakeRules:
    def all(self) -> list[dict[str, Any]]:
        return [{"pattern": "recertified", "condition": "manufacturer_recertified"}]


class FakeIngestion:
    """Foresees what it is set to, and keeps what it was asked."""

    def __init__(self, verdict: Verdict | None = None) -> None:
        self.verdict = verdict or Verdict("recorded")
        self.asked: list[tuple[str, CollectedPage]] = []

    def foresee(self, store: str, page: CollectedPage) -> Verdict:
        self.asked.append((store, page))
        return self.verdict


class FakeCollector:
    """Answers a preview as it is set to, and keeps what it was asked."""

    def __init__(self, answer: dict[str, Any]) -> None:
        self.answer = answer
        self.asked: list[dict[str, Any]] = []

    def preview(self, source: dict[str, Any]) -> dict[str, Any]:
        self.asked.append(source)
        return self.answer


def service(collector: FakeCollector, ingestion: FakeIngestion | None = None) -> PreviewService:
    return PreviewService(
        cast(ConditionRuleService, FakeRules()),
        cast(IngestionService, ingestion or FakeIngestion()),
        cast(CollectorClient, collector),
    )


OFFER = {
    "url": "https://orbit.test/products/exos-x18",
    "aliases": [],
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

    def test_an_offer_is_foreseen_as_ingestion_would_take_it_under_the_sources_key(
        self,
    ) -> None:
        collector = FakeCollector({"status": "found", "reason": None, "offer": OFFER})
        ingestion = FakeIngestion(Verdict("queued", "capacity_conflict"))
        source: PagePreview = TypeAdapter(SourcePreviewInput).validate_python(
            {"name": "Orbit", "kind": "shopify", "base_url": "https://orbit.test",
             "settings": {"collections": ["all"]}}
        )  # fmt: skip

        preview = service(collector, ingestion).preview_source(source)

        assert ingestion.asked == [
            ("orbit", CollectedPage(
                url=OFFER["url"], seller="", mpn="ST18000NM000J", condition="new",
                title=OFFER["title"], capacity_gb=20000, aliases=[], in_stock=True,
            ))
        ]  # fmt: skip
        # Waiting for review, as a preview calls it.
        assert preview["verdict"] == {"outcome": "review", "reason": "capacity_conflict"}
