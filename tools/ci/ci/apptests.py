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

The selection logic is pure and unit-tested; only :func:`run_tests` shells out.
"""

from __future__ import annotations

import json
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
) -> tuple[int, bool]:
    """Run each project's existing tiers in one pytest invocation. Returns (exit_code, ran_any).

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
    return rc, ran_any


def js_script_for_tier(tier: str | None) -> str:
    """The npm script for a tier: gated default suite → ``test``, a tier → ``test:<tier>``."""
    return "test" if tier is None else f"test:{tier}"


def _js_scripts(package_json: Path) -> dict[str, str]:
    try:
        return json.loads(package_json.read_text()).get("scripts") or {}
    except (json.JSONDecodeError, OSError):
        return {}


def discover_js_projects(repo_root: str | Path) -> list[str]:
    """Repo-relative dirs under stacks/ whose ``package.json`` declares a ``test`` script."""
    root = Path(repo_root)
    rels = {
        p.parent.relative_to(root).as_posix()
        for p in root.glob("stacks/**/package.json")
        if "node_modules" not in p.parts and "test" in _js_scripts(p)
    }
    return sorted(rels)


def run_js_tests(
    repo_root: str | Path, projects: list[str], tier: str | None, runner=subprocess.run
) -> tuple[int, bool]:
    """Run each JS project's npm test script for the tier. Returns (exit_code, ran_any).

    Installs with ``npm ci`` then runs ``npm run <script>`` (``test`` for the default
    suite, ``test:<tier>`` for an explicit tier). Projects with no such script are
    skipped, so a JS app only runs the tiers it actually defines.
    """
    root = Path(repo_root)
    script = js_script_for_tier(tier)
    rc = 0
    ran_any = False
    for rel in projects:
        proj = root / rel
        if script not in _js_scripts(proj / "package.json"):
            continue
        ran_any = True
        print(f"==> {rel} : npm run {script}")
        if runner(["npm", "ci"], cwd=proj).returncode != 0:
            rc = 1
            continue
        if runner(["npm", "run", script], cwd=proj).returncode != 0:
            rc = 1
    return rc, ran_any
