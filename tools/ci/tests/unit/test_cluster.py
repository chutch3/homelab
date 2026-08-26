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
from ci.cluster import (
    UPDATE_FORMAT,
    ClusterUnreachable,
    Service,
    StackState,
    SwarmCluster,
)

STACK_LS = ["docker", "stack", "ls", "--format", "{{.Name}}"]
SERVICE_LS = ["docker", "service", "ls", "--format", "{{.Name}}\t{{.Replicas}}"]


def inspect_of(*services: str) -> list[str]:
    return ["docker", "service", "inspect", "--format", UPDATE_FORMAT, *services]


# ── Service: one row of `service ls`, and the rules that read it ────────────

def test_service_reads_running_over_desired_from_the_replicas_column():
    service = Service.from_row("dns_dns-server", "2/3")
    assert (service.running, service.desired) == (2, 3)


def test_service_ignores_the_placement_suffix_swarm_appends():
    assert Service.from_row("a_b", "1/1 (max 1 per node)").at_desired_replicas


def test_service_never_reports_an_unreadable_replicas_column_as_converged():
    """`?` is not a count, so it cannot be evidence that anything is running."""
    assert not Service.from_row("a_b", "?").at_desired_replicas
    assert not Service.from_row("a_b", "?").converged


def test_service_short_of_its_desired_replicas_is_not_converged():
    assert not Service.from_row("a_b", "0/1").converged


@pytest.mark.parametrize("update", ["updating", "paused", "rollback_started"])
def test_service_under_an_unfinished_update_is_not_settled(update):
    """The outgoing task still counts toward `Replicas` while the new one starts."""
    service = Service.from_row("a_b", "1/1", update)
    assert service.at_desired_replicas
    assert not service.settled
    assert not service.converged


@pytest.mark.parametrize("update", ["none", "completed", "rollback_completed"])
def test_service_at_desired_replicas_with_a_finished_update_is_converged(update):
    assert Service.from_row("a_b", "1/1", update).converged


def test_service_defaults_to_no_update_when_none_is_reported():
    assert Service.from_row("a_b", "1/1").update == "none"


class TestSwarmCluster:
    """`SwarmCluster` — what the cluster says exists, and what has converged."""

    @pytest.fixture
    def subject(self, container, commands):
        """The cluster under test, over what `stack ls` / `service ls` report."""

        def _subject(stacks: str = "", services: str = "", updates: str = "") -> SwarmCluster:
            responds(
                commands,
                CommandResult(0, stacks),
                CommandResult(0, services),
                CommandResult(0, updates),
            )
            return container.cluster()

        return _subject

    def test_state_a_stack_not_listed_is_absent(self, subject):
        cluster = subject(stacks="authentik\n", services="authentik_server\t1/1\n")
        assert cluster.state("paperless") is StackState.ABSENT

    def test_state_every_service_at_its_desired_replicas_is_converged(self, subject):
        cluster = subject(
            stacks="paperless\n",
            services="paperless_web\t1/1\npaperless_db\t2/2\n",
        )
        assert cluster.state("paperless") is StackState.CONVERGED

    def test_state_a_single_service_short_of_desired_leaves_the_stack_present(self, subject):
        cluster = subject(
            stacks="paperless\n",
            services="paperless_web\t1/1\npaperless_db\t0/1\n",
        )
        assert cluster.state("paperless") is StackState.PRESENT

    def test_state_a_listed_stack_with_no_services_yet_is_present(self, subject):
        cluster = subject(stacks="paperless\n", services="")
        assert cluster.state("paperless") is StackState.PRESENT

    def test_state_attributes_a_service_to_the_longest_stack_name_prefixing_it(self, subject):
        cluster = subject(
            stacks="actual\nactual_server\n",
            services="actual_web\t1/1\nactual_server_actual_mcp\t0/1\n",
        )
        assert cluster.state("actual") is StackState.CONVERGED
        assert cluster.state("actual_server") is StackState.PRESENT

    def test_state_ignores_a_service_belonging_to_no_listed_stack(self, subject):
        cluster = subject(stacks="paperless\n", services="orphan_svc\t0/1\n")
        assert cluster.state("paperless") is StackState.PRESENT

    def test_states_only_ever_reads(self, subject, commands):
        subject(stacks="paperless\n", services="paperless_web\t1/1\n").states()
        assert argvs(commands) == [STACK_LS, SERVICE_LS, inspect_of("paperless_web")]

    def test_state_reads_the_cluster_once_however_many_stacks_are_asked_about(self, subject, commands):
        cluster = subject(stacks="a\nb\n", services="a_x\t1/1\nb_y\t1/1\n")
        cluster.state("a")
        cluster.state("b")
        cluster.state("c")
        assert argvs(commands) == [STACK_LS, SERVICE_LS, inspect_of("a_x", "b_y")]

    def test_state_a_service_still_updating_is_not_converged_at_full_replicas(self, subject):
        """The outgoing task still counts toward `Replicas` while the new one starts."""
        cluster = subject(
            stacks="dns\n",
            services="dns_dns-server\t1/1\n",
            updates="dns_dns-server\tupdating\n",
        )
        assert cluster.state("dns") is StackState.PRESENT

    def test_state_a_finished_update_is_converged(self, subject):
        cluster = subject(
            stacks="dns\n",
            services="dns_dns-server\t1/1\n",
            updates="dns_dns-server\tcompleted\n",
        )
        assert cluster.state("dns") is StackState.CONVERGED

    def test_state_a_service_never_updated_is_converged(self, subject):
        cluster = subject(
            stacks="dns\n",
            services="dns_dns-server\t1/1\n",
            updates="dns_dns-server\tnone\n",
        )
        assert cluster.state("dns") is StackState.CONVERGED

    @pytest.mark.parametrize("state", ["updating", "rollback_started", "paused"])
    def test_state_an_unfinished_update_holds_the_whole_stack_back(self, subject, state):
        """One service mid-update is enough: its dependents must not proceed."""
        cluster = subject(
            stacks="paperless\n",
            services="paperless_web\t1/1\npaperless_db\t1/1\n",
            updates=f"paperless_web\tcompleted\npaperless_db\t{state}\n",
        )
        assert cluster.state("paperless") is StackState.PRESENT

    def test_states_asks_nothing_of_a_cluster_with_no_services(self, subject, commands):
        subject(stacks="paperless\n", services="").states()
        assert argvs(commands) == [STACK_LS, SERVICE_LS]

    def test_states_an_unreachable_cluster_fails_naming_the_command_and_its_error(self, subject, commands):
        cluster = subject()
        responds(commands, CommandResult(1, "", "Cannot connect to the Docker daemon"))
        with pytest.raises(ClusterUnreachable) as exc:
            cluster.states()
        assert "docker stack ls" in str(exc.value)
        assert "Cannot connect to the Docker daemon" in str(exc.value)
