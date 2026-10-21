"""The rules that read a condition from listing text, in order. Each method works on the session
of the operation that calls it and never commits."""

from typing import Any

from sqlalchemy import delete
from sqlalchemy.orm import Session

from disktracker.catalog.models import ConditionRule


class ConditionRuleRepository:
    def replace(self, session: Session, rules: list[dict[str, Any]]) -> None:
        """These rules, in this order, in place of the ones kept before."""
        session.execute(delete(ConditionRule))
        session.add_all(ConditionRule(position=index, **rule) for index, rule in enumerate(rules))
