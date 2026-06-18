from __future__ import annotations

from math import ceil, floor


class Pacer:
    """Spreads a remaining daily budget evenly across the ticks left before reset.

    Never dumps the whole budget at once: when an even split rounds below 1, it
    still allows a floor of 1 per tick, so a small budget trickles out over the
    early ticks rather than all at once.
    """

    def __init__(self, poll_interval_sec: float) -> None:
        self._poll_interval_sec = poll_interval_sec

    def allowance(self, remaining: int, seconds_to_reset: float) -> int:
        if remaining <= 0:
            return 0
        ticks_left = max(1, ceil(seconds_to_reset / self._poll_interval_sec))
        per_tick = max(1, floor(remaining / ticks_left))
        return min(remaining, per_tick)
