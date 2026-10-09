import logging
import threading
from collections.abc import Callable

import pytest
from listing_text.readers import ConditionRules

from collector.errors import DisktrackerUnavailable
from collector.models import RunSummary
from collector.schedule import Schedule
from disktracker_api.models import SourceView
from tests.builders import CONDITION_RULES, source_view
from tests.fakes import FakeDisktracker


class ScriptedCollector:
    """A collector whose runs of each source complete, fail or crash as scripted; it keeps
    what it was asked to collect, and can stop the schedule."""

    def __init__(
        self,
        outcomes: dict[str, list[bool | Exception]] | None = None,
        stop_after: int | None = None,
        stop: threading.Event | None = None,
    ) -> None:
        self.outcomes = outcomes or {}
        self.collected: list[tuple[str, ConditionRules]] = []
        self.stop_after, self.stop = stop_after, stop

    def collect(self, source: SourceView, conditions: ConditionRules) -> RunSummary:
        self.collected.append((source.key, conditions))
        if self.stop is not None and len(self.collected) == self.stop_after:
            self.stop.set()
        scripted = self.outcomes.get(source.key, [True])
        runs = sum(key == source.key for key, _ in self.collected)
        outcome = scripted[min(runs, len(scripted)) - 1]
        if isinstance(outcome, Exception):
            raise outcome
        return RunSummary(source=source.key, completed=outcome)


MakeSchedule = Callable[..., Schedule]
A, B = source_view("a"), source_view("b")


class TestSchedule:
    @pytest.fixture
    def subject(self) -> MakeSchedule:
        def make(
            disktracker: FakeDisktracker, collector: ScriptedCollector, run_once: bool = True
        ) -> Schedule:
            return Schedule(disktracker, collector, run_once=run_once, poll_seconds=0)

        return make

    def test_a_single_round_succeeds_only_when_every_due_source_completes(
        self, subject: MakeSchedule
    ) -> None:
        stop = threading.Event()
        both = FakeDisktracker(due=[A, B])

        assert subject(both, ScriptedCollector()).run(stop) == 0
        assert subject(both, ScriptedCollector({"b": [False]})).run(stop) == 1
        assert subject(FakeDisktracker(), ScriptedCollector()).run(stop) == 0

    def test_each_due_source_is_collected_with_the_condition_rules_as_they_are_now(
        self, subject: MakeSchedule
    ) -> None:
        collector = ScriptedCollector()

        subject(FakeDisktracker(due=[A, B], conditions=CONDITION_RULES), collector).run(
            threading.Event()
        )

        assert collector.collected == [("a", CONDITION_RULES), ("b", CONDITION_RULES)]

    def test_condition_rules_are_asked_for_only_when_something_is_due(
        self, subject: MakeSchedule
    ) -> None:
        idle, busy = FakeDisktracker(), FakeDisktracker(due=[A])

        subject(idle, ScriptedCollector()).run(threading.Event())
        subject(busy, ScriptedCollector()).run(threading.Event())

        assert (idle.journal, busy.journal) == (
            ["due sources"],
            ["due sources", "condition rules", "due sources"],
        )

    def test_a_crashing_run_is_logged_with_its_traceback_and_the_next_source_still_runs(
        self, subject: MakeSchedule, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        collector = ScriptedCollector({"a": [KeyError("variants")]})

        code = subject(FakeDisktracker(due=[A, B]), collector).run(threading.Event())

        assert (code, [key for key, _ in collector.collected]) == (1, ["a", "b"])
        [crash] = caplog.records
        assert (
            crash.message,
            crash.levelname,
            crash.__dict__["source"],
            crash.__dict__["error"],
        ) == ("run_crashed", "ERROR", "a", "KeyError('variants')")
        assert crash.exc_info is not None and crash.exc_info[0] is KeyError

    def test_without_run_once_what_is_due_is_asked_and_collected_on_every_poll_until_stopped(
        self, subject: MakeSchedule
    ) -> None:
        stop = threading.Event()
        disktracker = FakeDisktracker(due=[A])
        collector = ScriptedCollector({"a": [True, RuntimeError("bug"), True]}, 3, stop)

        code = subject(disktracker, collector, run_once=False).run(stop)

        assert (code, len(collector.collected)) == (0, 3)
        # Each round asks until nothing it has not already run is due: twice here.
        assert disktracker.journal.count("due sources") == 6

    def test_what_is_due_is_asked_again_after_each_run_so_a_source_asked_for_meanwhile_goes_next(
        self, subject: MakeSchedule
    ) -> None:
        # While A runs, C is asked to run: it is due ahead of B, which was waiting.
        c = source_view("c")
        disktracker = FakeDisktracker(polls=[[A, B], [c, B], [B], []])
        collector = ScriptedCollector()

        code = subject(disktracker, collector).run(threading.Event())

        assert (code, [key for key, _ in collector.collected]) == (0, ["a", "c", "b"])

    def test_a_source_still_due_after_its_run_is_not_run_again_in_the_same_round(
        self, subject: MakeSchedule
    ) -> None:
        """A run whose report disktracker did not take leaves its source due: it waits for the
        next round, rather than running over and over."""
        disktracker = FakeDisktracker(due=[A, B])
        collector = ScriptedCollector()

        subject(disktracker, collector).run(threading.Event())

        assert [key for key, _ in collector.collected] == ["a", "b"]

    def test_a_round_that_loses_disktracker_partway_fails_having_run_what_it_could(
        self, subject: MakeSchedule
    ) -> None:
        disktracker = FakeDisktracker(polls=[[A, B], DisktrackerUnavailable("sources: HTTP 503")])
        collector = ScriptedCollector()

        code = subject(disktracker, collector).run(threading.Event())

        assert (code, [key for key, _ in collector.collected]) == (1, ["a"])

    def test_a_round_that_cannot_learn_what_is_due_fails_and_the_next_round_still_runs(
        self, subject: MakeSchedule, caplog: pytest.LogCaptureFixture
    ) -> None:
        caplog.set_level(logging.INFO, logger="collector")
        stop = threading.Event()
        collector = ScriptedCollector(stop_after=1, stop=stop)
        unavailable = FakeDisktracker(due=DisktrackerUnavailable("sources: HTTP 503"))
        recovering = FakeDisktracker(polls=[DisktrackerUnavailable("sources: HTTP 503"), [A]])

        assert subject(unavailable, ScriptedCollector()).run(threading.Event()) == 1
        subject(recovering, collector, run_once=False).run(stop)

        assert [key for key, _ in collector.collected] == ["a"]
        assert [
            (record.message, record.levelname, record.__dict__["error"])
            for record in caplog.records
        ] == [("sources_unavailable", "ERROR", "sources: HTTP 503")] * 2
