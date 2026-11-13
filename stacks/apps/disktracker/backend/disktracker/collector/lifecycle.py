"""How a collection run's life goes, decided apart from how runs are kept
(collector.run_repository): whether a start sent again is the run already registered, whether an
update applies to a run that may have ended, and how a run its collector no longer has ends."""

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from disktracker.errors import RunConflict

RESTARTED = "The collector restarted, or stopped working on it, before it ended."
SUPERSEDED = "A newer run of this store started before it ended."


def same_start(registered: Mapping[str, Any], sent: Mapping[str, Any]) -> None:
    """A start sent again under a run's id is that run: the same source started at the same
    moment. Any other is refused."""
    if (registered["source"], registered["started_at"]) != (sent["source"], sent["started_at"]):
        raise RunConflict("This run id was used for another run.")


def applies(status: str, kept: Mapping[str, Any], sent: Mapping[str, Any]) -> bool:
    """Whether an update is taken: by a running run, always. A run that has ended stays as it
    ended: the same end sent again changes nothing (False), and anything else is refused."""
    if status == "running":
        return True
    if dict(kept) != dict(sent):
        raise RunConflict(f"This run has already ended: {status}.")
    return False


def abandoned(reason: str, now: datetime) -> dict[str, Any]:
    """What a run its collector no longer has becomes: abandoned, ended now, for this reason."""
    return {"status": "abandoned", "updated_at": now, "finished_at": now, "reason": reason}
