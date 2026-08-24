"""The outer ring: thin objects we own that wrap the filesystem, subprocess,
the clock and stdout.

Nothing here has logic worth testing — that is the point. Every module that
would otherwise reach for ``open()``, ``subprocess.run()``, ``datetime.now()``
or ``print()`` takes one of these instead, so tests substitute a fake we own
rather than patching a third-party or stdlib name.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class FileSystem:
    """Reads the working tree. The only place the CI tool touches disk."""

    def glob(self, root: Path, pattern: str) -> list[Path]:
        return sorted(root.glob(pattern))

    def read_text(self, path: Path) -> str:
        return path.read_text()

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_dir(self, path: Path) -> bool:
        return path.is_dir()


@dataclass(frozen=True)
class CommandResult:
    """What a subprocess did, without exposing subprocess to callers."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class CommandRunner:
    """Runs external commands (git, gh, uv, npm, ansible-playbook)."""

    def run(
        self,
        argv: list[str],
        cwd: Path | None = None,
        capture: bool = False,
        check: bool = False,
    ) -> CommandResult:
        completed = subprocess.run(
            argv, cwd=cwd, capture_output=capture, text=True, check=check
        )
        return CommandResult(
            completed.returncode, completed.stdout or "", completed.stderr or ""
        )


class Clock:
    """Wall-clock time, so anything with a cutoff can be tested at a fixed instant."""

    def now_timestamp(self) -> float:
        return datetime.now(tz=timezone.utc).timestamp()


class Console:
    """Process output. Injected so tests assert on what was written, not capsys."""

    def out(self, message: str = "") -> None:
        print(message)

    def err(self, message: str = "") -> None:
        print(message, file=sys.stderr)


class Environment:
    """``.env`` overlaid with the process environment, which wins.

    `task ...` hands .env to a command via the Taskfile's ``dotenv:``; running
    the CLI directly does not, and the two must not disagree about what is on.
    """

    def __init__(self, filesystem: FileSystem, process_env: dict[str, str] | None = None) -> None:
        self._fs = filesystem
        self._process_env = dict(os.environ) if process_env is None else dict(process_env)

    def values(self, repo_root: str | Path) -> dict[str, str]:
        merged = dict(self._read_dotenv(Path(repo_root) / ".env"))
        merged.update(self._process_env)
        return merged

    def _read_dotenv(self, path: Path) -> dict[str, str]:
        if not self._fs.exists(path):
            return {}
        values: dict[str, str] = {}
        for line in self._fs.read_text(path).splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key, value = key.strip(), value.strip()
            if not key.replace("_", "").isalnum():
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key] = value
        return values
