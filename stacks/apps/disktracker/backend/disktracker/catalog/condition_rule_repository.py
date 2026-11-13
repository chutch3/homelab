"""The rules that read a condition from listing text, in order."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session, scoped_session

from disktracker.catalog.models import ConditionRule


class ConditionRuleRepository:
    def __init__(self, session: scoped_session[Session]) -> None:
        self.session = session

    def all(self) -> list[dict[str, Any]]:
        """Every rule, in the order they are tried."""
        rules = self.session.scalars(select(ConditionRule).order_by(ConditionRule.position))
        return [{"pattern": rule.pattern, "condition": rule.condition} for rule in rules]

    def replace(self, rules: list[dict[str, Any]]) -> None:
        """These rules, in this order, in place of the ones kept before."""
        self.session.execute(delete(ConditionRule))
        self.session.add_all(
            ConditionRule(position=index, **rule) for index, rule in enumerate(rules)
        )
