"""Fakes for the outer ring, and the container fixtures that inject them.

These stand in for :mod:`ci.adapters` — objects we own — so no test patches a
stdlib or third-party name. Anything a test wants to assert about a boundary
(what argv was run, what was printed) is recorded here.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from dependency_injector import providers

from ci.adapters import CommandResult
from ci.containers import Container

ROOT = Path("/repo")


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a pathlib glob to a regex, matching `**` across directories."""
    out = ""
    for part in pattern.split("/"):
        if part == "**":
            out += r"(?:[^/]+/)*"
        else:
            out += re.escape(part).replace(r"\*", r"[^/]*") + "/"
    return re.compile("^" + out.rstrip("/") + "$")


class FakeFileSystem:
    """An in-memory tree: {repo-relative path: file contents}."""

    def __init__(self, files: dict[str, str] | None = None, root: Path = ROOT) -> None:
        self.root = root
        self.files = {k.strip("/"): v for k, v in (files or {}).items()}
        self.reads: list[str] = []

    def _rel(self, path: Path) -> str:
        return Path(path).as_posix().removeprefix(self.root.as_posix()).strip("/")

    def glob(self, root: Path, pattern: str) -> list[Path]:
        base = self._rel(root)
        prefix = f"{base}/" if base else ""
        matcher = _glob_to_regex(pattern)
        hits = [f for f in self.files if f.startswith(prefix) and matcher.match(f[len(prefix):])]
        return sorted(self.root / h for h in hits)

    def read_text(self, path: Path) -> str:
        rel = self._rel(path)
        self.reads.append(rel)
        return self.files[rel]

    def exists(self, path: Path) -> bool:
        rel = self._rel(path)
        return rel in self.files or any(f.startswith(rel + "/") for f in self.files)

    def is_dir(self, path: Path) -> bool:
        rel = self._rel(path)
        return any(f.startswith(rel + "/") for f in self.files)


class FakeCommandRunner:
    """Records every argv it was asked to run and replays queued results."""

    def __init__(self, results: list[CommandResult] | None = None) -> None:
        self.calls: list[dict] = []
        self._results = list(results or [])

    def run(self, argv, cwd=None, capture=False, check=False) -> CommandResult:
        self.calls.append({"argv": list(argv), "cwd": cwd, "capture": capture, "check": check})
        return self._results.pop(0) if self._results else CommandResult(0)

    @property
    def argvs(self) -> list[list[str]]:
        return [c["argv"] for c in self.calls]


class FixedClock:
    def __init__(self, timestamp: float = 1_700_000_000.0) -> None:
        self.timestamp = timestamp

    def now_timestamp(self) -> float:
        return self.timestamp


class RecordingConsole:
    def __init__(self) -> None:
        self.stdout: list[str] = []
        self.stderr: list[str] = []

    def out(self, message: str = "") -> None:
        self.stdout.append(message)

    def err(self, message: str = "") -> None:
        self.stderr.append(message)

    @property
    def text(self) -> str:
        return "\n".join(self.stdout)


@pytest.fixture
def filesystem() -> FakeFileSystem:
    return FakeFileSystem()


@pytest.fixture
def commands() -> FakeCommandRunner:
    return FakeCommandRunner()


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def console() -> RecordingConsole:
    return RecordingConsole()


@pytest.fixture
def container(filesystem, commands, clock, console) -> Container:
    """A container with every outer-ring provider overridden by a fake."""
    c = Container()
    c.config.repo_root.from_value(str(ROOT))
    c.filesystem.override(providers.Object(filesystem))
    c.commands.override(providers.Object(commands))
    c.clock.override(providers.Object(clock))
    c.console.override(providers.Object(console))
    return c


REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def repo_container() -> Container:
    """A real container pointed at this repository — the integration seam."""
    c = Container()
    c.config.repo_root.from_value(str(REPO_ROOT))
    return c
