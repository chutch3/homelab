"""`SwarmCluster` against a real Swarm, on a throwaway single-node cluster.

The unit suite feeds it replica columns written by hand, so it proves the
parsing but not that Docker still prints what we parse — and it never observes
``PRESENT``, because every stack in the homelab is converged.

Runs against the local daemon only: the context is pinned to ``default`` and
the suite skips if that daemon is missing. A swarm it starts is a swarm it
leaves.
"""

from __future__ import annotations

import subprocess
import time

import pytest

from ci.adapters import Subprocess
from ci.cluster import SERVICE_LS, StackState, SwarmCluster, parse_replicas

PROBE = "ci-plan-probe"
CONVERGED = "ci-plan-ok"
NEVER_DEPLOYED = "ci-plan-absent"
IMAGE = "alpine:3"
TIMEOUT_SECONDS = 180

# `stuck` carries a constraint no node satisfies, so its task never leaves
# pending and the service sits at 0/1 — which is what makes the stack PRESENT.
PROBE_COMPOSE = f"""
services:
    ready:
        image: {IMAGE}
        command: ["sleep", "600"]
    stuck:
        image: {IMAGE}
        command: ["sleep", "600"]
        deploy:
            placement:
                constraints: ["node.labels.{PROBE} == yes"]
"""

CONVERGED_COMPOSE = f"""
services:
    ready:
        image: {IMAGE}
        command: ["sleep", "600"]
"""

SETTLED = {
    f"{CONVERGED}_ready": "1/1",
    f"{PROBE}_ready": "1/1",
    f"{PROBE}_stuck": "0/1",
}


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
def swarm(tmp_path_factory):
    """A single-node swarm on the local daemon, carrying the two probe stacks."""
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

        try:
            tmp = tmp_path_factory.mktemp("probe")
            for stack, compose in ((PROBE, PROBE_COMPOSE), (CONVERGED, CONVERGED_COMPOSE)):
                (path := tmp / f"{stack}.yml").write_text(compose)
                docker("stack", "deploy", "-c", str(path), stack)
            _await_settled()
            yield
        finally:
            for stack in (PROBE, CONVERGED):
                docker("stack", "rm", stack, check=False)
            if ours:
                docker("swarm", "leave", "--force", check=False)
    finally:
        patch.undo()


@pytest.mark.e2e
def test_state_reports_each_stack_as_the_cluster_actually_holds_it(swarm):
    cluster = SwarmCluster(Subprocess())
    assert {name: cluster.state(name) for name in (CONVERGED, PROBE, NEVER_DEPLOYED)} == {
        CONVERGED: StackState.CONVERGED,
        PROBE: StackState.PRESENT,
        NEVER_DEPLOYED: StackState.ABSENT,
    }


@pytest.mark.e2e
def test_parse_replicas_reads_every_column_a_real_swarm_prints(swarm):
    assert (columns := replicas()), "the probe stacks should have produced services"
    assert all(parse_replicas(column)[0] >= 0 for column in columns.values()), columns
