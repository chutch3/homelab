"""Trying a store before it is collected: one offer as the collector reads it from a source,
saved or not, or the sources that would read the store a product page is from; each with what
recording the offer would do. Nothing is kept."""

from typing import Any

from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.drive_service import DriveService
from disktracker.catalog.rules import normalize_mpn, preview_verdict
from disktracker.collection.client import CollectorClient
from disktracker.collection.schemas import PagePreview, SourceInspectionInput
from disktracker.collection.service import source_key


class PreviewService:
    def __init__(
        self, rules: ConditionRuleService, drives: DriveService, collector: CollectorClient
    ) -> None:
        self.rules, self.drives, self.collector = rules, drives, collector

    def _condition_rules(self) -> list[dict[str, Any]]:
        return self.rules.all()

    def _verdict_on(self, offer: dict[str, Any]) -> dict[str, str | None]:
        """What disktracker would do with an offer the collector read, were it recorded."""
        known = None
        if offer["mpn"]:
            known = self.drives.capacity(normalize_mpn(offer["mpn"]))
        outcome, reason = preview_verdict(offer, known)
        return {"outcome": outcome, "reason": reason}

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
        offer = preview["offer"]
        return {**preview, "verdict": None if offer is None else self._verdict_on(offer)}

    def inspect_link(self, entry: SourceInspectionInput) -> dict[str, Any]:
        """The sources that would read the store a product page is from, best first, each with
        the offer it reads from that page and what recording it would do."""
        inspected = self.collector.inspect(
            {"url": entry.url, "transport": entry.transport, "conditions": self._condition_rules()}
        )
        candidates = [
            {**candidate, "verdict": self._verdict_on(candidate["offer"])}
            for candidate in inspected["candidates"]
        ]
        return {**inspected, "candidates": candidates}
