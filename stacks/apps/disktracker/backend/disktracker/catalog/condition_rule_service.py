"""Replacing the rules that read a condition from listing text, as one piece of work. They are
read through catalog.reads."""

from collections.abc import Sequence
from typing import Any

from disktracker.catalog.condition_rule_repository import ConditionRuleRepository
from disktracker.catalog.schemas import ConditionRule
from disktracker.database import SessionFactory


class ConditionRuleService:
    def __init__(self, session_factory: SessionFactory, rules: ConditionRuleRepository) -> None:
        self.session_factory, self.rules = session_factory, rules

    def replace(self, rules: Sequence[ConditionRule]) -> list[dict[str, Any]]:
        """The rules, in the order given, in place of the ones kept before."""
        kept = [rule.model_dump() for rule in rules]
        with self.session_factory() as session:
            self.rules.replace(session, kept)
            session.commit()
        return kept
