from warden.repositories.ledger import SearchLedgerRepository


class TestSearchLedgerRepository:
    def test_spent_is_zero_for_unknown_window(self, repo: SearchLedgerRepository):
        assert repo.spent("2026-06-16") == 0

    def test_add_accumulates_within_window(self, repo: SearchLedgerRepository):
        repo.add("2026-06-16", 3)
        repo.add("2026-06-16", 2)
        assert repo.spent("2026-06-16") == 5

    def test_windows_are_isolated(self, repo: SearchLedgerRepository):
        repo.add("2026-06-16", 4)
        assert repo.spent("2026-06-17") == 0
