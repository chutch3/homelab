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


@runtime_checkable
class Output(Protocol):
    """The program's answer on stdout.

    Only for output a caller consumes: JSON a workflow parses, an image list a
    shell loops over, the plan rows, and a subprocess's own streams passed
    through untouched. Diagnostics are not this — services log those, so they
    reach stderr without being mistaken for the payload.
    """

    def line(self, text: str = "") -> None:
        """One line of payload on stdout."""
        ...

    def raw(self, text: str) -> None:
        """Payload written to stdout exactly as given — no newline added."""
        ...

    def raw_err(self, text: str) -> None:
        """A subprocess's own stderr, passed through unchanged."""
        ...
