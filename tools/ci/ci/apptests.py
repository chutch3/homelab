"""Run the apps' pytest suites by tier — the ``ci test`` subcommand.

Discovery is structural: any dir under ``stacks/`` with a ``pyproject.toml`` is a
testable project (each declares its own pytest dev-group, so ``uv run pytest``
self-bootstraps). Tiers are ``tests/{unit,integration,e2e}`` subdirs, run if they
exist.

The default (gated) run executes unit + integration **together in one pytest**, so
the project's ``--cov-fail-under`` applies to the *combined* coverage of both tiers.
A single explicit ``--tier`` runs that tier alone and clears ``addopts`` (a partial
run shouldn't trip the coverage gate). e2e is not in the default suite — it's run
explicitly via ``--tier e2e`` (the e2e workflow).

The selection logic is pure and unit-tested; only :func:`run_tests` shells out.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

TIERS = ("unit", "integration", "e2e")
# The gated default suite: unit + integration, coverage measured across both.
DEFAULT_TIERS = ("unit", "integration")


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


def tiers_to_run(tier: str | None) -> list[str]:
    """No tier → the default gated suite (unit+integration); else that single tier."""
    if tier is None:
        return list(DEFAULT_TIERS)
    if tier in TIERS:
        return [tier]
    raise ValueError(f"unknown tier {tier!r} (want unit|integration|e2e)")


def run_tests(
    repo_root: str | Path, projects: list[str], tiers: list[str], gated: bool = True, runner=subprocess.run
) -> int:
    """Run each project's existing tiers in one pytest invocation. Returns an exit code.

    ``gated`` keeps the project's ``addopts`` so ``--cov-fail-under`` applies to the
    combined coverage of all tiers run together; otherwise ``addopts`` is cleared
    (a single explicit tier is a partial run and shouldn't be coverage-gated).
    """
    root = Path(repo_root)
    rc = 0
    ran_any = False
    for rel in projects:
        proj = root / rel
        present = [t for t in tiers if (proj / "tests" / t).is_dir()]
        if not present:
            continue
        ran_any = True
        print(f"==> {rel} : {' '.join(present)}")
        paths = [f"tests/{t}" for t in present]
        extra = [] if gated else ["-o", "addopts="]
        result = runner(["uv", "run", "pytest", *paths, *extra], cwd=proj)
        if result.returncode != 0:
            rc = 1
    if not ran_any:
        print("No matching test tiers.")
    return rc
