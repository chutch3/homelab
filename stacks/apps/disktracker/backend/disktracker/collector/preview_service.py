"""Trying a store before it is collected: one offer as the collector reads it from a source,
saved or not, or the sources that would read the store a product page is from; each with what
recording the offer would do. Nothing is kept."""

from typing import Any

from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.ingestion_service import CollectedPage, IngestionService
from disktracker.catalog.verdict import Verdict
from disktracker.collector.client import CollectorClient
from disktracker.collector.schemas import PagePreview, SourceInspectionInput
from disktracker.collector.source_service import source_key

OUTCOMES = {"recorded": "recorded", "queued": "review", "ignored": "ignored"}


def shown(verdict: Verdict) -> dict[str, str | None]:
    return {"outcome": OUTCOMES[verdict.outcome], "reason": verdict.reason}


class PreviewService:
    def __init__(
        self, rules: ConditionRuleService, ingestion: IngestionService, collector: CollectorClient
    ) -> None:
        self.rules, self.ingestion, self.collector = rules, ingestion, collector

    def preview_source(self, source: PagePreview) -> dict[str, Any]:
        """One offer as the collector reads it from a source, saved or not, and what recording
        it would do."""
        preview = self.collector.preview(
            {
                "key": source_key(source.name),
                "kind": source.kind,
                "base_url": source.base_url,
                "transport": source.transport,
                "obey_robots": source.obey_robots,
                "settings": source.settings.model_dump(),
                "conditions": self.rules.all(),
                "page_url": source.page_url or None,
            }
        )
        if preview["offer"] is None:
            return {**preview, "verdict": None}
        page = CollectedPage.model_validate(preview["offer"])
        return {**preview, "verdict": shown(self.ingestion.foresee(source_key(source.name), page))}

    def inspect_link(self, entry: SourceInspectionInput) -> dict[str, Any]:
        """The sources that would read the store a product page is from, best first, each with
        the offer it reads from that page and what recording it would do."""
        inspected = self.collector.inspect(
            {"url": entry.url, "transport": entry.transport, "conditions": self.rules.all()}
        )
        # Of a store not collected yet: no listing of it was decided, and none of its offers kept.
        candidates = [
            {
                **candidate,
                "verdict": shown(
                    self.ingestion.foresee("", CollectedPage.model_validate(candidate["offer"]))
                ),
            }
            for candidate in inspected["candidates"]
        ]
        return {**inspected, "candidates": candidates}
