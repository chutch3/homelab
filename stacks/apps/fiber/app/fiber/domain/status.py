from __future__ import annotations

from datetime import datetime
from enum import Enum

from fiber.domain.models import MovementOutcome
from fiber.domain.schedule import is_overdue


class DBStatus(str, Enum):
    CLEAN = "clean"
    STRAINING = "straining"
    CLOGGED = "clogged"
    CONSTIPATED = "constipated"
    PINCHED = "pinched"
    MISCONFIGURED = "misconfigured"


def derive_status(
    *,
    misconfigured: bool,
    running: bool,
    last_outcome: MovementOutcome | None,
    last_success: datetime | None,
    schedule: str,
    now: datetime,
) -> DBStatus:
    if misconfigured:
        return DBStatus.MISCONFIGURED
    if running:
        return DBStatus.STRAINING
    if last_outcome is MovementOutcome.CLOGGED:
        return DBStatus.CLOGGED
    if is_overdue(last_success, schedule, now):
        return DBStatus.CONSTIPATED
    if last_outcome is MovementOutcome.PINCHED:
        return DBStatus.PINCHED
    return DBStatus.CLEAN
