"""The rules that read a condition from listing text, in order. Each method works on the session
of the operation that calls it and never commits."""

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from disktracker.catalog.models import ConditionRule


class ConditionRuleRepository:
    def all(self, session: Session) -> list[dict[str, Any]]:
        """Every rule, in the order they are tried."""
        rules = session.scalars(select(ConditionRule).order_by(ConditionRule.position))
        return [{"pattern": rule.pattern, "condition": rule.condition} for rule in rules]

    def replace(self, session: Session, rules: list[dict[str, Any]]) -> None:
        """These rules, in this order, in place of the ones kept before."""
        session.execute(delete(ConditionRule))
        session.add_all(ConditionRule(position=index, **rule) for index, rule in enumerate(rules))
