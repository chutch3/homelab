"""The rules that read a condition from listing text: read in the order they are tried, and
replaced as one piece of work."""

from collections.abc import Sequence
from typing import Any

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

    def replace(self, rules: Sequence[ConditionRule]) -> list[dict[str, Any]]:
        """The rules, in the order given, in place of the ones kept before."""
        kept = [rule.model_dump() for rule in rules]
        with self.session_factory() as session:
            self.rules.replace(session, kept)
            session.commit()
        return kept
