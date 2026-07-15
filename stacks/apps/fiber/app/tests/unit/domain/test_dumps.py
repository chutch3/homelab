from datetime import datetime, timezone

from fiber.domain.dumps import classify, plan_sweep
from fiber.domain.models import BowlEntry


# ---------------------------------------------------------------------------
# classify — Bristol-scale size health
# ---------------------------------------------------------------------------

def test_no_baseline_is_normal() -> None:
    assert classify(size_bytes=1234, baseline_median=None) == 4
    assert classify(size_bytes=1234, baseline_median=0) == 4


def test_ratio_thresholds() -> None:
    base = 1000
    assert classify(size_bytes=100, baseline_median=base) == 1    # <=0.2x suspiciously tiny
    assert classify(size_bytes=300, baseline_median=base) == 2    # <=0.5x
    assert classify(size_bytes=800, baseline_median=base) == 3    # <=0.9x
    assert classify(size_bytes=1000, baseline_median=base) == 4   # ~1x healthy
    assert classify(size_bytes=1300, baseline_median=base) == 5   # <=1.5x
    assert classify(size_bytes=1800, baseline_median=base) == 6   # <=2x
    assert classify(size_bytes=5000, baseline_median=base) == 7   # >2x bloated


# ---------------------------------------------------------------------------
# plan_sweep — retention
# ---------------------------------------------------------------------------

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
