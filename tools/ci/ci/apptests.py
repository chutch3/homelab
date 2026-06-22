"""Run the apps' pytest suites by tier — the ``ci test`` subcommand.

Discovery is structural: any dir under ``stacks/`` with a ``pyproject.toml`` is a
testable project (each declares its own pytest dev-group, so ``uv run pytest``
self-bootstraps). Tiers are ``tests/{unit,integration,e2e}`` subdirs, run if they
exist. Coverage gating is a unit-tier concern, so non-unit tiers clear the
project's ``addopts`` (otherwise ``--cov-fail-under`` trips on a partial run).

The selection logic is pure and unit-tested; only :func:`run_tests` shells out.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

TIERS = ("unit", "integration", "e2e")


def discover_test_projects(repo_root: str | Path) -> list[str]:
    """Repo-relative dirs under stacks/ that contain a ``pyproject.toml``."""
    root = Path(repo_root)
    rels = {
        p.parent.relative_to(root).as_posix()
        for p in root.glob("stacks/**/pyproject.toml")
        if ".venv" not in p.parts
    }
    return sorted(rels)


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


def tiers_to_run(tier: str) -> list[str]:
    if tier == "all":
        return list(TIERS)
    if tier in TIERS:
        return [tier]
    raise ValueError(f"unknown tier {tier!r} (want unit|integration|e2e|all)")


def run_tests(repo_root: str | Path, projects: list[str], tiers: list[str], runner=subprocess.run) -> int:
    """Run ``uv run pytest tests/<tier>`` for each existing (project, tier). Returns an exit code."""
    root = Path(repo_root)
    rc = 0
    ran_any = False
    for rel in projects:
        proj = root / rel
        for tier in tiers:
            if not (proj / "tests" / tier).is_dir():
                continue
            ran_any = True
            print(f"==> {rel} : {tier}")
            # Coverage gate (e.g. --cov-fail-under) is a unit-tier concern; a partial
            # run of integration/e2e would otherwise fail it on ~0% coverage.
            extra = [] if tier == "unit" else ["-o", "addopts="]
            result = runner(["uv", "run", "pytest", f"tests/{tier}", *extra], cwd=proj)
            if result.returncode != 0:
                rc = 1
    if not ran_any:
        print("No matching test tiers.")
    return rc
