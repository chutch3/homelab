"""`SwarmCluster` against a real Swarm, on a throwaway single-node cluster.

The unit suite feeds :class:`SwarmCluster` replica columns written by hand, so
it proves the parsing but not that Docker still prints what we parse. It also
never observes ``PRESENT``: every stack in the homelab is converged, so the one
state that means "deployed but not there yet" has only ever existed in a fake.

This deploys two probe stacks and reads them back:

  ci-plan-probe   one service converges, one can never be scheduled  -> PRESENT
  ci-plan-ok      one service, converged                             -> CONVERGED
  ci-plan-absent  never deployed                                     -> ABSENT

It runs against the **local** daemon only, never the operator's cluster: the
context is pinned to ``default`` for the whole module and the suite skips if
that daemon is missing. A swarm it initialised is a swarm it leaves.
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
pytestmark = pytest.mark.e2e

IMAGE = "alpine:3"
TIMEOUT_SECONDS = 180

# `stuck` carries a constraint no node satisfies, so its task never leaves
# pending and the service sits at 0/1 — which is what makes the stack PRESENT
# rather than CONVERGED. `ready` is what proves the difference is real.
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


def docker(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["docker", *args], capture_output=True, text=True, check=check)


def state_of(stack: str) -> StackState:
    """A fresh cluster each call — `SwarmCluster` caches, so polling needs a new one."""
    return SwarmCluster(Subprocess()).state(stack)


def _await(stack: str, wanted: StackState) -> None:
    deadline = time.monotonic() + TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        if (seen := state_of(stack)) is wanted:
            return
        time.sleep(2)
    raise AssertionError(f"{stack} was {seen.value}, not {wanted.value}, after {TIMEOUT_SECONDS}s")


@pytest.fixture(scope="module")
def swarm(tmp_path_factory):
    """A single-node swarm on the local daemon, carrying the two probe stacks."""
    patch = pytest.MonkeyPatch()
    patch.setenv("DOCKER_CONTEXT", "default")
    patch.delenv("DOCKER_HOST", raising=False)
    try:
        probe = docker("info", "--format", "{{.Swarm.LocalNodeState}}", check=False)
        if probe.returncode != 0:
            pytest.skip(f"no local docker daemon: {probe.stderr.strip()}")

        ours = probe.stdout.strip() == "inactive"
        if ours and (init := docker(
            "swarm", "init", "--advertise-addr", "127.0.0.1", check=False
        )).returncode != 0:
            pytest.skip(f"cannot init a local swarm: {init.stderr.strip()}")

        try:
            tmp = tmp_path_factory.mktemp("probe")
            for stack, compose in ((PROBE, PROBE_COMPOSE), (CONVERGED, CONVERGED_COMPOSE)):
                path = tmp / f"{stack}.yml"
                path.write_text(compose)
                docker("stack", "deploy", "-c", str(path), stack)
            _await(CONVERGED, StackState.CONVERGED)
            _await(PROBE, StackState.PRESENT)
            yield
        finally:
            for stack in (PROBE, CONVERGED):
                docker("stack", "rm", stack, check=False)
            if ours:
                docker("swarm", "leave", "--force", check=False)
    finally:
        patch.undo()


def test_state_a_stack_short_of_its_replicas_is_present(swarm):
    assert state_of(PROBE) is StackState.PRESENT


def test_state_a_stack_at_its_desired_replicas_is_converged(swarm):
    assert state_of(CONVERGED) is StackState.CONVERGED


def test_state_a_stack_that_was_never_deployed_is_absent(swarm):
    assert state_of(NEVER_DEPLOYED) is StackState.ABSENT


def test_parse_replicas_reads_every_column_a_real_swarm_prints(swarm):
    """The guard against Docker changing the column out from under the parser."""
    rows = [
        line.partition("\t")
        for line in docker(*SERVICE_LS[1:]).stdout.splitlines()
        if line.strip()
    ]
    assert rows, "the probe stacks should have produced services to read"
    for name, _, replicas in rows:
        running, _ = parse_replicas(replicas)
        assert running >= 0, f"{name}: unparsed replicas column {replicas!r}"
