"""`ci plan` end to end: the real CLI against a real Swarm.

Everything below the command line is exercised for real — argv parsing, the
composition root, the stack tree, dependency resolution, the cluster read, and
the rendered plan on stdout. The only fixture is the world: a throwaway
single-node swarm carrying stacks whose compose files are also the repo the CLI
is pointed at, so the manifest and the deployment cannot disagree.

It is also the only place ``PRESENT`` is observed, since every stack in the
homelab is converged.

Runs against the local daemon only: the context is pinned to ``default`` and
the suite skips if that daemon is missing. A swarm it starts is a swarm it
leaves.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

from ci.cluster import SERVICE_LS

OK = "ci-plan-ok"  # deployed, converges
PROBE = "ci-plan-probe"  # deployed, one service can never schedule
ABSENT = "ci-plan-absent"  # declared in the repo, never deployed
IMAGE = "alpine:3"
TIMEOUT_SECONDS = 180

SERVICE = f"""
services:
    ready:
        image: {IMAGE}
        command: ["sleep", "600"]
"""

# `stuck` carries a constraint no node satisfies, so its task never leaves
# pending and the service sits at 0/1 — which is what makes the stack PRESENT.
PROBE_SERVICE = SERVICE + f"""    stuck:
        image: {IMAGE}
        command: ["sleep", "600"]
        deploy:
            placement:
                constraints: ["node.labels.{PROBE} == yes"]
"""

REPO = {
    OK: SERVICE,
    ABSENT: SERVICE,
    PROBE: f"x-homelab:\n    requires: [{OK}]\n" + PROBE_SERVICE,
}
DEPLOYED = (OK, PROBE)
SETTLED = {f"{OK}_ready": "1/1", f"{PROBE}_ready": "1/1", f"{PROBE}_stuck": "0/1"}


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


def replicas() -> dict[str, str]:
    """What `docker service ls` reports, read without the code under test."""
    rows = (line.partition("\t") for line in docker(*SERVICE_LS[1:]).stdout.splitlines())
    return {name: column for name, _, column in rows if name}


def _await_settled() -> None:
    """Wait on Docker's own view, so the assertions are not just echoing setup."""
    seen: dict[str, str] = {}
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if (seen := {k: v for k, v in replicas().items() if k in SETTLED}) == SETTLED:
            return
        time.sleep(2)
    raise AssertionError(f"probe stacks settled at {seen}, wanted {SETTLED}")


@pytest.fixture(scope="module")
def repo(tmp_path_factory):
    """A repo of probe stacks, deployed to a throwaway swarm on the local daemon."""
    patch = pytest.MonkeyPatch()
    patch.setenv("DOCKER_CONTEXT", "default")
    patch.delenv("DOCKER_HOST", raising=False)
    try:
        node = docker("info", "--format", "{{.Swarm.LocalNodeState}}", check=False)
        if node.returncode != 0:
            pytest.skip(f"no local docker daemon: {node.stderr.strip()}")

        ours = node.stdout.strip() == "inactive"
        if ours and (init := docker(
            "swarm", "init", "--advertise-addr", "127.0.0.1", check=False
        )).returncode != 0:
            pytest.skip(f"cannot init a local swarm: {init.stderr.strip()}")

        root = tmp_path_factory.mktemp("repo")
        for stack, compose in REPO.items():
            path = root / "stacks" / "apps" / stack / "docker-compose.yml"
            path.parent.mkdir(parents=True)
            path.write_text(compose)
        try:
            for stack in DEPLOYED:
                docker("stack", "deploy", "-c", str(compose_of(root, stack)), stack)
            _await_settled()
            yield root
        finally:
            for stack in DEPLOYED:
                docker("stack", "rm", stack, check=False)
            if ours:
                docker("swarm", "leave", "--force", check=False)
    finally:
        patch.undo()


def compose_of(root: Path, stack: str) -> Path:
    return root / "stacks" / "apps" / stack / "docker-compose.yml"


def ci(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the real CLI as its own process, against the probe repo."""
    return subprocess.run(
        [sys.executable, "-m", "ci.cli", *args, "--repo-root", str(root)],
        capture_output=True,
        text=True,
    )


def plan_of(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [" ".join(line.split()) for line in result.stdout.splitlines()]


@pytest.mark.e2e
def test_deploy_plans_every_stack_with_the_state_the_cluster_actually_holds(repo):
    result = ci(repo, "plan")
    assert result.returncode == 0, result.stderr
    assert plan_of(result) == [
        f"deploy {ABSENT} absent",
        f"skip {OK} converged",
        f"deploy {PROBE} present",
    ]
    assert "3 stack(s), 2 to deploy — plan only, nothing deployed." in result.stderr


@pytest.mark.e2e
def test_deploy_leaves_a_converged_stack_out_of_the_work_a_re_run_would_do(repo):
    """Check I on deploy: what is already converged is not in the work to do."""
    plan = json.loads(ci(repo, "plan", "--json").stdout)
    assert [row for row in plan if row["action"] == "deploy"] == [
        {"stack": ABSENT, "state": "absent", "action": "deploy"},
        {"stack": PROBE, "state": "present", "action": "deploy"},
    ]


@pytest.mark.e2e
def test_deploy_names_the_target_that_pulled_in_each_dependency(repo):
    result = ci(repo, "plan", PROBE)
    assert result.returncode == 0, result.stderr
    assert plan_of(result) == [
        f"skip {OK} converged → required by {PROBE}",
        f"deploy {PROBE} present → explicit target",
    ]


@pytest.mark.e2e
def test_deploy_leaves_the_cluster_exactly_as_it_found_it(repo):
    before = replicas()
    ci(repo, "plan")
    assert replicas() == before
