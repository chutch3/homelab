"""Tests for what the cluster's facts mean for a deploy (`ci.stackstate`).

The dangerous case is calling a stack CONVERGED when it is not — a plan that
says so is a plan that skips work the cluster still needs. Nothing here touches
docker: these are facts in, verdict out.
"""

from __future__ import annotations

import pytest

from ci.stackstate import Service, StackState, stack_states


def service(name: str, stack: str, replicas: str = "1/1", update: str = "none") -> Service:
    return Service.from_row(name, stack, replicas, update)


# ── Service: one service, and the rules that read it ────────────────────────

def test_service_reads_running_over_desired_from_the_replicas_column():
    assert (service("a_b", "a", "2/3").running, service("a_b", "a", "2/3").desired) == (2, 3)


def test_service_ignores_the_placement_suffix_swarm_appends():
    assert service("a_b", "a", "1/1 (max 1 per node)").at_desired_replicas


def test_service_never_reports_an_unreadable_replicas_column_as_converged():
    """`?` is not a count, so it cannot be evidence that anything is running."""
    assert not service("a_b", "a", "?").at_desired_replicas
    assert not service("a_b", "a", "?").converged


def test_service_short_of_its_desired_replicas_is_not_converged():
    assert not service("a_b", "a", "0/1").converged


@pytest.mark.parametrize("update", ["updating", "paused", "rollback_started"])
def test_service_under_an_unfinished_update_is_not_settled(update):
    """The outgoing task still counts toward `Replicas` while the new one starts."""
    subject = service("a_b", "a", "1/1", update)
    assert subject.at_desired_replicas
    assert not subject.settled
    assert not subject.converged


@pytest.mark.parametrize("update", ["none", "completed", "rollback_completed"])
def test_service_at_desired_replicas_with_a_finished_update_is_converged(update):
    assert service("a_b", "a", "1/1", update).converged


# ── stack_states: the verdict per stack ─────────────────────────────────────

def test_stack_states_every_service_at_its_desired_replicas_is_converged():
    states = stack_states([service("paperless_web", "paperless"),
                           service("paperless_db", "paperless", "2/2")])
    assert states == {"paperless": StackState.CONVERGED}


def test_stack_states_a_single_service_short_of_desired_leaves_the_stack_present():
    states = stack_states([service("paperless_web", "paperless"),
                           service("paperless_db", "paperless", "0/1")])
    assert states == {"paperless": StackState.PRESENT}


def test_stack_states_one_service_mid_update_holds_the_whole_stack_back():
    """Its dependents must not proceed against the tasks it is replacing."""
    states = stack_states([service("paperless_web", "paperless"),
                           service("paperless_db", "paperless", "1/1", "updating")])
    assert states == {"paperless": StackState.PRESENT}


def test_stack_states_reports_each_stack_separately():
    states = stack_states([service("a_x", "a"), service("b_y", "b", "0/1")])
    assert states == {"a": StackState.CONVERGED, "b": StackState.PRESENT}


def test_stack_states_attributes_by_label_not_by_name_prefix():
    """`actual_server_actual_mcp` belongs to `actual_server`, never to `actual`."""
    states = stack_states([service("actual_web", "actual"),
                           service("actual_server_actual_mcp", "actual_server", "0/1")])
    assert states == {"actual": StackState.CONVERGED, "actual_server": StackState.PRESENT}


def test_stack_states_ignores_a_service_that_belongs_to_no_stack():
    assert stack_states([service("loose", "")]) == {}


def test_stack_states_a_stack_it_never_saw_is_absent_to_the_caller():
    """Nothing deployed has that label, so it is simply not in the map."""
    assert stack_states([service("a_x", "a")]).get("paperless", StackState.ABSENT) is (
        StackState.ABSENT
    )
