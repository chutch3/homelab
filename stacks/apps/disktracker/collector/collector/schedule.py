"""Running the sources disktracker says are due, once, or on every poll until stopped. Which
sources are due, and how they are configured, is asked afresh before each run, so schedules,
Run now and other changes made on disktracker's Admin page apply without a restart, and a
source asked to run while another is running goes next rather than after everything already
waiting. A crash in one source's run is logged with its traceback and does not stop the others,
or the next round."""

import logging
import threading
from typing import Protocol

from listing_text.readers import ConditionRules

from collector.errors import DisktrackerUnavailable
from collector.models import RunSummary
from collector.ports import Disktracker
from disktracker_api.models import SourceView

log = logging.getLogger(__name__)


class Collects(Protocol):
    def collect(self, source: SourceView, conditions: ConditionRules) -> RunSummary: ...


class Schedule:
    def __init__(
        self, disktracker: Disktracker, collector: Collects, run_once: bool, poll_seconds: float
    ) -> None:
        self.disktracker, self.collector = disktracker, collector
        self.run_once, self.poll_seconds = run_once, poll_seconds

    def run(self, stop: threading.Event) -> int:
        """The process exit status: after one round when running once, else when stopped.
        Each round collects the sources due then, one after another."""
        while True:
            succeeded = self._round()
            if self.run_once:
                return 0 if succeeded else 1
            if stop.wait(self.poll_seconds):
                return 0

    def _round(self) -> bool:
        """Whether the round learnt what was due and every run of it completed. The round runs
        the first source due, asks again, and so on until nothing is due that it has not run: a
        source still due after its run (its report was lost, say) waits for the next round.
        Conditions are read by the rules as they are when each run starts."""
        ran: set[str] = set()
        completed: list[bool] = []
        while True:
            try:
                due = [source for source in self.disktracker.due_sources() if source.key not in ran]
                if not due:
                    return all(completed)
                conditions = self.disktracker.condition_rules()
            except DisktrackerUnavailable as error:
                log.error("sources_unavailable", extra={"error": str(error)})
                return False
            ran.add(due[0].key)
            # Every due source is collected, whatever became of the ones before it.
            completed.append(self._completed(due[0], conditions))

    def _completed(self, source: SourceView, conditions: ConditionRules) -> bool:
        try:
            return self.collector.collect(source, conditions).completed
        except Exception as error:
            log.exception("run_crashed", extra={"source": source.key, "error": repr(error)})
            return False
