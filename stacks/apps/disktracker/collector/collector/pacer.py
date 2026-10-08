"""Spacing requests to each site at least its crawl delay apart."""

from collector.clock import Clock


class Pacer:
    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.last_turn: dict[str, float] = {}

    def wait_turn(self, site: str, delay: float | None) -> None:
        """Wait until this site's delay has passed since its last request, then take a turn."""
        if delay and site in self.last_turn:
            wait = self.last_turn[site] + delay - self.clock.monotonic()
            if wait > 0:
                self.clock.sleep(wait)
        self.last_turn[site] = self.clock.monotonic()
