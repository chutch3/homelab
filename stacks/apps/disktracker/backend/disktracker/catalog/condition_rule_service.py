"""The rules that read a condition from listing text: read in the order they are tried, replaced
as one piece of work, and used to read what pasted listing text says of a drive."""

from collections.abc import Sequence
from typing import Any

from listing_facts.listing import read_listing
from listing_facts.readers import condition_rules

from disktracker.catalog.condition_rule_repository import ConditionRuleRepository
from disktracker.catalog.schemas import ConditionRule
from disktracker.database import Transactions


class ConditionRuleService:
    def __init__(
        self,
        transactions: Transactions,
        rules: ConditionRuleRepository,
    ) -> None:
        self.transactions = transactions
        self.rules = rules

    def all(self) -> list[dict[str, Any]]:
        with self.transactions.begin(reads=True):
            return self.rules.all()

    def read_listing(self, text: str) -> dict[str, object]:
        """What pasted listing text says of a drive (MPN, capacity, condition, brand, price),
        its condition read by the rules as they are now; null for what it does not say."""
        conditions = condition_rules((rule["pattern"], rule["condition"]) for rule in self.all())
        return read_listing(text, conditions)._asdict()

    def replace(self, rules: Sequence[ConditionRule]) -> list[dict[str, Any]]:
        """The rules, in the order given, in place of the ones kept before."""
        with self.transactions.begin():
            kept = [rule.model_dump() for rule in rules]
            self.rules.replace(kept)
            return kept
