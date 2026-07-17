from __future__ import annotations

from dataclasses import dataclass

from warden.models import RootFolder


@dataclass(frozen=True)
class SpaceVerdict:
    blocked: bool
    free_bytes: int         # smallest free space across the source's root folders
    projected_bytes: int    # free_bytes minus bytes still downloading in the queue
    path: str               # the tightest root folder (the one free_bytes came from)


class SpaceGuard:
    """Decides whether low disk should pause hunting.

    Projected headroom = the smallest free space across a source's *arr root folders,
    minus the bytes still downloading in its queue (in-flight grabs that haven't landed
    yet). Hunting is blocked when that headroom falls below the configured floor, so
    warden stops asking for new releases before the disk actually fills.

    A floor of 0 disables the guard. When no root folder reports free space (all
    inaccessible), ``evaluate`` returns ``None`` so the caller can fail open.
    """

    def __init__(self, min_free_bytes: int) -> None:
        self._min = min_free_bytes

    @property
    def enabled(self) -> bool:
        return self._min > 0

    def evaluate(self, root_folders: list[RootFolder], committed_bytes: int) -> SpaceVerdict | None:
        if not root_folders:
            return None
        tightest = min(root_folders, key=lambda rf: rf.free_space)
        projected = tightest.free_space - committed_bytes
        return SpaceVerdict(blocked=projected < self._min, free_bytes=tightest.free_space,
                            projected_bytes=projected, path=tightest.path)
