"""The outer ring: the real implementations of :mod:`ci.ports`.

Nothing here has logic worth testing — that is the point. Anything that needed
a decision (merging .env with the process environment) lives in :mod:`ci.config`
as a pure function instead.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class CommandResult:
    """What a subprocess did, without exposing subprocess to callers."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class LocalFileSystem:
    def glob(self, root: Path, pattern: str) -> list[Path]:
        return sorted(root.glob(pattern))

    def read_text(self, path: Path) -> str:
        return path.read_text()

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()


class Subprocess:
    def run(
        self,
        argv: list[str],
        cwd: Path | None = None,
        capture: bool = False,
        check: bool = False,
    ) -> CommandResult:
        completed = subprocess.run(argv, cwd=cwd, capture_output=capture, text=True, check=check)
        return CommandResult(completed.returncode, completed.stdout or "", completed.stderr or "")


class SystemClock:
    def now_timestamp(self) -> float:
        return datetime.now(tz=timezone.utc).timestamp()


class StdoutConsole:
    def out(self, message: str = "") -> None:
        print(message)

    def err(self, message: str = "") -> None:
        print(message, file=sys.stderr)

    def write(self, text: str) -> None:
        sys.stdout.write(text)
