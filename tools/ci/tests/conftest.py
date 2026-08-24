"""Fakes for the outer ring, and the container fixtures that inject them.

These stand in for :mod:`ci.ports` — interfaces we own — so no test patches a
stdlib or third-party name. The command boundary is a ``Mock(spec=CommandRunner)``
so ``assert_called_with`` validates it; the filesystem is a hand fake because it
is stateful and a Mock would say nothing useful about a tree.

``test_ports.py`` asserts every fake here still satisfies the port it stands for.
"""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import Mock

import pytest
from dependency_injector import providers

from ci.adapters import CommandResult
from ci.containers import Container
from ci.ports import CommandRunner

ROOT = Path("/repo")
REPO_ROOT = Path(__file__).resolve().parents[3]


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a pathlib glob to a regex, matching `**` across directories."""
    out = ""
    for part in pattern.split("/"):
        out += r"(?:[^/]+/)*" if part == "**" else re.escape(part).replace(r"\*", r"[^/]*") + "/"
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
        return any(f.startswith(self._rel(path) + "/") for f in self.files)


class FixedClock:
    def __init__(self, timestamp: float = 1_700_000_000.0) -> None:
        self.timestamp = timestamp

    def now_timestamp(self) -> float:
        return self.timestamp


class RecordingConsole:
    def __init__(self) -> None:
        self.stdout: list[str] = []
        self.stderr: list[str] = []
        self.written: list[str] = []

    def out(self, message: str = "") -> None:
        self.stdout.append(message)

    def err(self, message: str = "") -> None:
        self.stderr.append(message)

    def write(self, text: str) -> None:
        self.written.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self.stdout)


def responds(commands: Mock, *results: CommandResult) -> None:
    """Queue results for the next calls; anything after them succeeds silently."""
    queued = list(results)
    commands.run.side_effect = lambda *a, **k: queued.pop(0) if queued else CommandResult(0)


def argvs(commands: Mock) -> list[list[str]]:
    """The argv of every command the runner was asked to run, in order."""
    return [call.args[0] for call in commands.run.call_args_list]


@pytest.fixture
def filesystem() -> FakeFileSystem:
    return FakeFileSystem()


@pytest.fixture
def commands() -> Mock:
    """The command boundary. `spec` stops a renamed method being silently spoofed."""
    mock = Mock(spec=CommandRunner)
    mock.run.return_value = CommandResult(0)
    return mock


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock()


@pytest.fixture
def console() -> RecordingConsole:
    return RecordingConsole()


@pytest.fixture
def env() -> dict[str, str]:
    """The merged environment the container hands to services. Empty by default."""
    return {}


@pytest.fixture
def container(filesystem, commands, clock, console, env) -> Container:
    """A container with every outer-ring provider overridden by a fake."""
    c = Container()
    c.config.repo_root.from_value(str(ROOT))
    c.config.env.from_value(env)
    c.filesystem.override(providers.Object(filesystem))
    c.commands.override(providers.Object(commands))
    c.clock.override(providers.Object(clock))
    c.console.override(providers.Object(console))
    return c


@pytest.fixture
def repo_container() -> Container:
    """A real container pointed at this repository — the integration seam."""
    from ci.config import load_env

    c = Container()
    c.config.repo_root.from_value(str(REPO_ROOT))
    c.config.env.from_value(load_env(c.filesystem(), REPO_ROOT, {}))
    return c
