"""The interfaces the CI tool depends on.

Services type-hint these, never the concrete classes in :mod:`ci.adapters`, so
a fake in a test satisfies the same declared contract the real adapter does.
They are ``runtime_checkable`` purely so the suite can assert that conformance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class FileSystem(Protocol):
    """Reads the working tree."""

    def glob(self, root: Path, pattern: str) -> list[Path]: ...

    def read_text(self, path: Path) -> str: ...

    def exists(self, path: Path) -> bool: ...

    def is_dir(self, path: Path) -> bool: ...


@runtime_checkable
class CommandRunner(Protocol):
    """Runs external commands (git, gh, uv, npm, ansible-playbook)."""

    def run(
        self,
        argv: list[str],
        cwd: Path | None = None,
        capture: bool = False,
        check: bool = False,
    ) -> "CommandOutcome": ...


@runtime_checkable
class CommandOutcome(Protocol):
    """What a command did."""

    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool: ...


@runtime_checkable
class Clock(Protocol):
    """Wall-clock time, so anything with a cutoff can be tested at a fixed instant."""

    def now_timestamp(self) -> float: ...
