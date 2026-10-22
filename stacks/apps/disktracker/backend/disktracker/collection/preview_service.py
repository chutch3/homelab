"""Trying a store before it is collected: one offer as the collector reads it from a source,
saved or not, or the sources that would read the store a product page is from; each with what
recording the offer would do. Nothing is kept."""

from typing import Any

from disktracker.catalog.acceptance import Verdict
from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.ingestion_service import IngestionService
from disktracker.collection.client import CollectorClient
from disktracker.collection.schemas import PagePreview, SourceInspectionInput
from disktracker.collection.service import source_key

# What a verdict's outcome is called where a preview shows it.
OUTCOMES = {"recorded": "recorded", "queued": "review", "ignored": "ignored"}


def shown(verdict: Verdict) -> dict[str, str | None]:
    return {"outcome": OUTCOMES[verdict.outcome], "reason": verdict.reason}


class PreviewService:
    def __init__(
        self, rules: ConditionRuleService, ingestion: IngestionService, collector: CollectorClient
    ) -> None:
        self.rules, self.ingestion, self.collector = rules, ingestion, collector

    def _condition_rules(self) -> list[dict[str, Any]]:
        return self.rules.all()

    def _verdict_on(self, offer: dict[str, Any], store: str) -> dict[str, str | None]:
        """What taking in an offer the collector read would make of it now, as ingestion would:
        under the store it would be collected as, with what disktracker knows of that store's
        listing and the drive it is of."""
        return shown(
            self.ingestion.foresee(
                store=store, url=offer["url"], seller=offer.get("seller") or "",
                mpn=offer["mpn"], condition=offer["condition"], title=offer["title"],
                capacity_gb=offer["capacity_gb"], aliases=offer["aliases"],
                in_stock=offer["in_stock"],
            )
        )  # fmt: skip

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
                "conditions": self._condition_rules(),
                "page_url": source.page_url or None,
            }
        )
        offer, store = preview["offer"], source_key(source.name)
        return {**preview, "verdict": None if offer is None else self._verdict_on(offer, store)}

    def inspect_link(self, entry: SourceInspectionInput) -> dict[str, Any]:
        """The sources that would read the store a product page is from, best first, each with
        the offer it reads from that page and what recording it would do."""
        inspected = self.collector.inspect(
            {"url": entry.url, "transport": entry.transport, "conditions": self._condition_rules()}
        )
        # Of a store not collected yet: no listing of it was decided, and none of its offers kept.
        candidates = [
            {**candidate, "verdict": self._verdict_on(candidate["offer"], store="")}
            for candidate in inspected["candidates"]
        ]
        return {**inspected, "candidates": candidates}
