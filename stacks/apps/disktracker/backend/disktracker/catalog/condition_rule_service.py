"""The rules that read a condition from listing text: read in the order they are tried, replaced
as one piece of work, and used to read what pasted listing text says of a drive."""

from collections.abc import Sequence
from typing import Any

from listing_text.listing import read_listing
from listing_text.readers import condition_rules

from disktracker.catalog.condition_rule_repository import ConditionRuleRepository
from disktracker.catalog.schemas import ConditionRule
from disktracker.database import SessionFactory


class ConditionRuleService:
    def __init__(
        self,
        session_factory: SessionFactory,
        snapshot_factory: SessionFactory,
        rules: ConditionRuleRepository,
    ) -> None:
        self.session_factory, self.snapshot_factory = session_factory, snapshot_factory
        self.rules = rules

    def all(self) -> list[dict[str, Any]]:
        with self.snapshot_factory() as session:
            return self.rules.all(session)

    def read_listing(self, text: str) -> dict[str, object]:
        """What pasted listing text says of a drive (MPN, capacity, condition, brand, price),
        its condition read by the rules as they are now; null for what it does not say."""
        conditions = condition_rules((rule["pattern"], rule["condition"]) for rule in self.all())
        return read_listing(text, conditions)._asdict()

    def replace(self, rules: Sequence[ConditionRule]) -> list[dict[str, Any]]:
        """The rules, in the order given, in place of the ones kept before."""
        kept = [rule.model_dump() for rule in rules]
        with self.session_factory() as session:
            self.rules.replace(session, kept)
            session.commit()
        return kept
