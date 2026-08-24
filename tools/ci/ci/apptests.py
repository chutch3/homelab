"""Run the apps' test suites by tier — the ``ci test`` subcommand.

Discovery is structural. A dir under ``stacks/`` with a ``pyproject.toml`` is a Python
project (each declares its own pytest dev-group, so ``uv run pytest`` self-bootstraps);
tiers are ``tests/{unit,integration,e2e}`` subdirs, run if they exist. A dir with a
``package.json`` declaring a ``test`` script is a JS project, run with npm (``npm ci``
then ``npm run test`` / ``test:<tier>``). An app can be both (e.g. a Python backend with
a browser-JS frontend), in which case ``ci test`` runs both.

The default (gated) run executes unit + integration **together in one pytest**, so
the project's ``--cov-fail-under`` applies to the *combined* coverage of both tiers.
A single explicit ``--tier`` runs that tier alone and clears ``addopts`` (a partial
run shouldn't trip the coverage gate). e2e is not in the default suite — it's run
explicitly via ``--tier e2e`` (the e2e workflow).

Selection is pure; :class:`TestSuites` takes the filesystem and command runner, so
its tests assert on the argv it would have run rather than running anything.
"""

from __future__ import annotations

import json
from pathlib import Path

from ci.adapters import CommandRunner, Console, FileSystem

TIERS = ("unit", "integration", "e2e")
# The gated default suite: unit + integration, coverage measured across both.
DEFAULT_TIERS = ("unit", "integration")


def select_projects(projects: list[str], selector: str | None) -> list[str]:
    """Filter projects by a bare name (a path segment) or a repo-relative path prefix."""
    if not selector:
        return list(projects)
    selected = []
    for rel in projects:
        if "/" in selector:  # a path: project at or under it
            if rel == selector or rel.startswith(selector + "/"):
                selected.append(rel)
        elif selector in rel.split("/"):  # a name: any path segment
            selected.append(rel)
    return selected


def tiers_to_run(tier: str | None) -> list[str]:
    """No tier → the default gated suite (unit+integration); else that single tier."""
    if tier is None:
        return list(DEFAULT_TIERS)
    if tier in TIERS:
        return [tier]
    raise ValueError(f"unknown tier {tier!r} (want unit|integration|e2e)")


def js_script_for_tier(tier: str | None) -> str:
    """The npm script for a tier: gated default suite → ``test``, a tier → ``test:<tier>``."""
    return "test" if tier is None else f"test:{tier}"


class TestSuites:
    """Discovers the apps' test projects and runs their tiers."""

    def __init__(
        self,
        filesystem: FileSystem,
        commands: CommandRunner,
        console: Console,
        repo_root: str | Path = ".",
    ) -> None:
        self._fs = filesystem
        self._commands = commands
        self._console = console
        self._root = Path(repo_root)

    def python_projects(self) -> list[str]:
        """Repo-relative dirs under stacks/ that contain a ``pyproject.toml``."""
        return sorted(
            {
                p.parent.relative_to(self._root).as_posix()
                for p in self._fs.glob(self._root, "stacks/**/pyproject.toml")
                if ".venv" not in p.parts
            }
        )

    def js_projects(self) -> list[str]:
        """Repo-relative dirs under stacks/ whose ``package.json`` declares a ``test`` script."""
        return sorted(
            {
                p.parent.relative_to(self._root).as_posix()
                for p in self._fs.glob(self._root, "stacks/**/package.json")
                if "node_modules" not in p.parts and "test" in self._scripts(p)
            }
        )

    def _scripts(self, package_json: Path) -> dict[str, str]:
        try:
            return json.loads(self._fs.read_text(package_json)).get("scripts") or {}
        except (json.JSONDecodeError, OSError):
            return {}

    def run_python(
        self, projects: list[str], tiers: list[str], gated: bool = True
    ) -> tuple[int, bool]:
        """Run each project's existing tiers in one pytest call. Returns (exit_code, ran_any).

        ``gated`` keeps the project's ``addopts`` so ``--cov-fail-under`` applies to the
        combined coverage of all tiers run together; otherwise ``addopts`` is cleared
        (a single explicit tier is a partial run and shouldn't be coverage-gated).
        """
        rc, ran_any = 0, False
        for rel in projects:
            proj = self._root / rel
            present = [t for t in tiers if self._fs.is_dir(proj / "tests" / t)]
            if not present:
                continue
            ran_any = True
            self._console.out(f"==> {rel} : {' '.join(present)}")
            paths = [f"tests/{t}" for t in present]
            extra = [] if gated else ["-o", "addopts="]
            if not self._commands.run(["uv", "run", "pytest", *paths, *extra], cwd=proj).ok:
                rc = 1
        return rc, ran_any

    def run_js(self, projects: list[str], tier: str | None) -> tuple[int, bool]:
        """Run each JS project's npm test script for the tier. Returns (exit_code, ran_any).

        Installs with ``npm ci`` then runs ``npm run <script>``. Projects with no such
        script are skipped, so a JS app only runs the tiers it actually defines.
        """
        script = js_script_for_tier(tier)
        rc, ran_any = 0, False
        for rel in projects:
            proj = self._root / rel
            if script not in self._scripts(proj / "package.json"):
                continue
            ran_any = True
            self._console.out(f"==> {rel} : npm run {script}")
            if not self._commands.run(["npm", "ci"], cwd=proj).ok:
                rc = 1
                continue
            if not self._commands.run(["npm", "run", script], cwd=proj).ok:
                rc = 1
        return rc, ran_any
