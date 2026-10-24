"""How a run's life goes, decided apart from how it is kept: a start sent again, an update to a run
that may have ended, and what becomes of a run its collector no longer has."""

from datetime import UTC, datetime
from typing import Any

import pytest

from disktracker.collector.lifecycle import RESTARTED, SUPERSEDED, abandoned, applies, same_start
from disktracker.errors import RunConflict

NOW = datetime(2026, 10, 22, 12, tzinfo=UTC)
STARTED = {"source": "serverpartdeals", "started_at": NOW}


def test_a_start_sent_again_is_the_same_run() -> None:
    same_start(STARTED, dict(STARTED))


@pytest.mark.parametrize(
    "other",
    [
        {**STARTED, "source": "goharddrive"},
        {**STARTED, "started_at": datetime(2026, 1, 1, tzinfo=UTC)},
    ],
)
def test_another_start_under_a_run_id_used_before_is_refused(other: dict[str, Any]) -> None:
    with pytest.raises(RunConflict, match="used for another run"):
        same_start(STARTED, other)


def test_a_running_run_takes_any_update() -> None:
    assert applies("running", {"seen": 3}, {"seen": 5})


def test_an_ended_run_takes_its_own_end_again_and_changes_nothing() -> None:
    assert not applies(
        "completed", {"status": "completed", "seen": 5}, {"status": "completed", "seen": 5}
    )


def test_an_ended_run_refuses_anything_else() -> None:
    with pytest.raises(RunConflict, match="already ended: completed"):
        applies("completed", {"status": "completed", "seen": 5}, {"status": "failed", "seen": 5})


@pytest.mark.parametrize("reason", [SUPERSEDED, RESTARTED])
def test_a_run_abandoned_ends_now_for_why(reason: str) -> None:
    assert abandoned(reason, NOW) == {
        "status": "abandoned",
        "updated_at": NOW,
        "finished_at": NOW,
        "reason": reason,
    }
