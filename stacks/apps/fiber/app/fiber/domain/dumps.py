from __future__ import annotations

from fiber.domain.models import BowlEntry


def classify(size_bytes: int, baseline_median: int | None) -> int:
    """Bristol-scale (1-7) size health: 4 = on baseline, 1 = suspiciously tiny, 7 = bloated."""
    if not baseline_median:
        return 4
    ratio = size_bytes / baseline_median
    if ratio <= 0.2:
        return 1
    if ratio <= 0.5:
        return 2
    if ratio <= 0.9:
        return 3
    if ratio <= 1.1:
        return 4
    if ratio <= 1.5:
        return 5
    if ratio <= 2.0:
        return 6
    return 7


def plan_sweep(entries: list[BowlEntry], retain: int) -> tuple[list[BowlEntry], list[BowlEntry]]:
    """Split Bowl entries into (finals to delete beyond retain, leftover temp dingleberries)."""
    dingleberries = [e for e in entries if e.is_temp]
    finals = sorted((e for e in entries if not e.is_temp), key=lambda e: e.modified_at)
    to_delete = finals[:-retain] if retain > 0 and len(finals) > retain else []
    return to_delete, dingleberries
