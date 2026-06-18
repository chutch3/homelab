from __future__ import annotations

from fiber.models import BowlEntry


def plan_sweep(entries: list[BowlEntry], retain: int) -> tuple[list[BowlEntry], list[BowlEntry]]:
    dingleberries = [e for e in entries if e.is_temp]
    finals = sorted((e for e in entries if not e.is_temp), key=lambda e: e.modified_at)
    to_delete = finals[:-retain] if retain > 0 and len(finals) > retain else []
    return to_delete, dingleberries
