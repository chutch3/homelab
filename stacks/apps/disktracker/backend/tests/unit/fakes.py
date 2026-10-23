"""Stand-ins shared by the unit tests of every module."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime

from disktracker.clock import Clock
from disktracker.database import Transactions


class FixedClock(Clock):
    """A clock stopped at one moment."""

    def __init__(self, moment: datetime) -> None:
        self.moment = moment

    def now(self) -> datetime:
        return self.moment


class FakeTransactions(Transactions):
    """Begins transactions that touch nothing, and keeps how each ended: kept, undone or read."""

    def __init__(self) -> None:
        self.ended: list[str] = []

    @contextmanager
    def begin(self, read_only: bool = False) -> Iterator[None]:
        try:
            yield
        except Exception:
            self.ended.append("undone")
            raise
        self.ended.append("read" if read_only else "kept")

    @property
    def committed(self) -> bool:
        return "kept" in self.ended
