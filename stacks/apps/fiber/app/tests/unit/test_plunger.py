from datetime import datetime, timezone
from fiber.models import BowlEntry
from fiber.plunger import plan_sweep


def _entry(name: str, minute: int, is_temp: bool = False) -> BowlEntry:
    return BowlEntry(path=name, size_bytes=10,
                     modified_at=datetime(2026, 6, 15, 3, minute, tzinfo=timezone.utc),
                     is_temp=is_temp)


def test_keeps_newest_n_finals_deletes_rest() -> None:
    entries = [_entry("a", 1), _entry("b", 2), _entry("c", 3)]
    to_delete, dingleberries = plan_sweep(entries, retain=2)
    assert [e.path for e in to_delete] == ["a"]  # oldest beyond keep-2
    assert dingleberries == []


def test_exactly_n_deletes_nothing() -> None:
    entries = [_entry("a", 1), _entry("b", 2)]
    to_delete, _ = plan_sweep(entries, retain=2)
    assert to_delete == []


def test_temp_artifacts_are_dingleberries_not_counted_in_retention() -> None:
    entries = [_entry("a", 1), _entry("b", 2), _entry("tmp", 3, is_temp=True)]
    to_delete, dingleberries = plan_sweep(entries, retain=2)
    assert [e.path for e in dingleberries] == ["tmp"]
    assert to_delete == []
