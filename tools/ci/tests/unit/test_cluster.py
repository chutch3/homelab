"""Tests for the live Swarm state a plan reports (`ci.cluster`).

The dangerous case is calling a stack CONVERGED when it is not — a plan that
says so is a plan that skips work the cluster still needs. Every read goes
through the command boundary, so these assert the exact argv as well as the
verdict: `--plan` must only ever list.
"""

from __future__ import annotations

import pytest

from conftest import argvs, responds

from ci.adapters import CommandResult
from ci.cluster import ClusterUnreachable, StackState, SwarmCluster, parse_replicas

STACK_LS = ["docker", "stack", "ls", "--format", "{{.Name}}"]
SERVICE_LS = ["docker", "service", "ls", "--format", "{{.Name}}\t{{.Replicas}}"]


@pytest.fixture
def subject(container, commands):
    """The cluster under test, over what `stack ls` / `service ls` are made to report."""

    def _subject(stacks: str = "", services: str = "") -> SwarmCluster:
        responds(commands, CommandResult(0, stacks), CommandResult(0, services))
        return container.cluster()

    return _subject


def test_parse_replicas_reads_running_over_desired():
    assert parse_replicas("2/3") == (2, 3)


def test_parse_replicas_ignores_the_placement_suffix_swarm_appends():
    assert parse_replicas("1/1 (max 1 per node)") == (1, 1)


def test_parse_replicas_never_reports_an_unreadable_column_as_converged():
    running, desired = parse_replicas("?")
    assert running != desired


class TestSwarmCluster:
    """`SwarmCluster` — what the cluster says exists, and what has converged."""

    def test_a_stack_not_listed_is_absent(self, subject):
        cluster = subject(stacks="authentik\n", services="authentik_server\t1/1\n")
        assert cluster.state("paperless") is StackState.ABSENT

    def test_every_service_at_its_desired_replicas_is_converged(self, subject):
        cluster = subject(
            stacks="paperless\n",
            services="paperless_web\t1/1\npaperless_db\t2/2\n",
        )
        assert cluster.state("paperless") is StackState.CONVERGED

    def test_a_single_service_short_of_desired_leaves_the_stack_present(self, subject):
        cluster = subject(
            stacks="paperless\n",
            services="paperless_web\t1/1\npaperless_db\t0/1\n",
        )
        assert cluster.state("paperless") is StackState.PRESENT

    def test_a_listed_stack_with_no_services_yet_is_present_not_converged(self, subject):
        cluster = subject(stacks="paperless\n", services="")
        assert cluster.state("paperless") is StackState.PRESENT

    def test_a_service_is_attributed_to_the_longest_stack_name_that_prefixes_it(self, subject):
        cluster = subject(
            stacks="actual\nactual_server\n",
            services="actual_web\t1/1\nactual_server_actual_mcp\t0/1\n",
        )
        assert cluster.state("actual") is StackState.CONVERGED
        assert cluster.state("actual_server") is StackState.PRESENT

    def test_a_service_belonging_to_no_listed_stack_is_ignored(self, subject):
        cluster = subject(stacks="paperless\n", services="orphan_svc\t0/1\n")
        assert cluster.state("paperless") is StackState.PRESENT

    def test_it_only_ever_lists(self, subject, commands):
        subject(stacks="paperless\n", services="paperless_web\t1/1\n").states()
        assert argvs(commands) == [STACK_LS, SERVICE_LS]

    def test_the_cluster_is_read_once_however_many_stacks_are_asked_about(self, subject, commands):
        cluster = subject(stacks="a\nb\n", services="a_x\t1/1\nb_y\t1/1\n")
        cluster.state("a")
        cluster.state("b")
        cluster.state("c")
        assert argvs(commands) == [STACK_LS, SERVICE_LS]

    def test_an_unreachable_cluster_fails_naming_the_command_and_its_error(self, subject, commands):
        cluster = subject()
        responds(commands, CommandResult(1, "", "Cannot connect to the Docker daemon"))
        with pytest.raises(ClusterUnreachable) as exc:
            cluster.states()
        assert "docker stack ls" in str(exc.value)
        assert "Cannot connect to the Docker daemon" in str(exc.value)
