from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

from warden.models import GrabEvent, SearchAttempt


@dataclass(frozen=True)
class Reconciliation:
    hits: tuple[str, ...]       # indexer name per confirmed hit (for per-indexer metrics)
    misses: int                 # attempts that aged out with no grab
    resolved: frozenset[int]    # remote_ids to drop from the pending ledger


class EfficacyTracker:
    """Pure policy: correlate searches warden fired against *arr grab history.

    A grab is a hit for an attempt when it lands for the same remote_id at or after
    the search time and wasn't an RSS grab (RSS would have grabbed it regardless).
    A miss is inferred by absence once an attempt ages past the resolve window.
    """

    def __init__(self, *, enabled: bool, resolve_window: timedelta) -> None:
        self.enabled = enabled
        self._window = resolve_window

    def reconcile(self, pending: Sequence[SearchAttempt], grabs: Sequence[GrabEvent],
                  now: datetime) -> Reconciliation:
        hits: list[str] = []
        resolved: list[int] = []
        misses = 0
        for a in pending:
            grab = next((g for g in grabs
                         if g.remote_id == a.remote_id and g.at >= a.searched_at
                         and g.release_source != "Rss"), None)
            if grab is not None:
                hits.append(grab.indexer)
                resolved.append(a.remote_id)
            elif now - a.searched_at >= self._window:
                misses += 1
                resolved.append(a.remote_id)
        return Reconciliation(tuple(hits), misses, frozenset(resolved))
