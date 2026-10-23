"""Stand-ins shared by the unit tests of every module."""

from datetime import datetime

from disktracker.clock import Clock


class FixedClock(Clock):
    """A clock stopped at one moment."""

    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment
