"""Tests for the deploy plan (`ci.deploy`) — order plus live state, printed.

A plan is only useful if it says what will happen rather than listing
everything, so the assertions here are about the two things that distinguish
the rows: the state each stack is already in, and why it is in the plan at all.
"""

from __future__ import annotations

import pytest

from conftest import argvs, responds

from ci.adapters import CommandResult
from ci.cluster import StackState

LABELS = 'services:\n    a:\n        deploy:\n            labels: [{}]\n'
TRAEFIK = LABELS.format('"traefik.enable=true"')
PROXY = "services: {}\n"
NEEDS_PROXY = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK
NEEDS_AUTH = "x-homelab:\n    requires: [reverse-proxy, authentik]\n" + LABELS.format(
    '"traefik.enable=true", "traefik.http.routers.p.middlewares=authentik@swarm"'
)

TREE = {
    "stacks/reverse-proxy/docker-compose.yml": PROXY,
    "stacks/apps/authentik/docker-compose.yml": NEEDS_PROXY,
    "stacks/apps/paperless/docker-compose.yml": NEEDS_AUTH,
}


@pytest.fixture
def tree(filesystem):
    filesystem.files.update(TREE)
    return filesystem


@pytest.fixture
def live(commands):
    """Seed what the cluster reports: stack names, then `service<TAB>replicas`."""

    def _live(stacks: str = "", services: str = "") -> None:
        responds(commands, CommandResult(0, stacks), CommandResult(0, services))

    return _live


@pytest.fixture
def plan(container, tree):
    return container.deploy_plan()


def rows_by_stack(rows):
    return {row.stack: row for row in rows}


class TestDeployPlanRows:
    """`DeployPlan.rows` — one row per stack the deploy would touch."""

    def test_a_stack_absent_from_the_cluster_reports_absent(self, plan, live):
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t1/1\n")
        rows = rows_by_stack(plan.rows(["paperless"]))
        assert rows["paperless"].state is StackState.ABSENT
        assert rows["authentik"].state is StackState.ABSENT

    def test_a_stack_at_its_desired_replicas_reports_converged(self, plan, live):
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t1/1\n")
        assert rows_by_stack(plan.rows(["paperless"]))["reverse-proxy"].state is StackState.CONVERGED

    def test_a_stack_deployed_but_short_of_its_replicas_reports_present(self, plan, live):
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t0/1\n")
        assert rows_by_stack(plan.rows(["paperless"]))["reverse-proxy"].state is StackState.PRESENT

    def test_an_explicit_target_says_so(self, plan, live):
        live()
        row = rows_by_stack(plan.rows(["paperless"]))["paperless"]
        assert row.verb == "deploy"
        assert row.reason == "explicit target"

    def test_a_dependency_names_the_target_that_required_it(self, plan, live):
        live()
        row = rows_by_stack(plan.rows(["paperless"]))["authentik"]
        assert row.verb == "ensure"
        assert row.reason == "required by paperless"

    def test_a_transitive_dependency_names_the_target_not_the_middle_stack(self, plan, live):
        live()
        assert rows_by_stack(plan.rows(["paperless"]))["reverse-proxy"].reason == "required by paperless"

    def test_a_dependency_of_several_targets_names_them_all(self, plan, live):
        live()
        rows = rows_by_stack(plan.rows(["paperless", "authentik"]))
        assert rows["reverse-proxy"].reason == "required by authentik, paperless"

    def test_a_target_that_is_also_a_dependency_is_still_an_explicit_target(self, plan, live):
        live()
        rows = rows_by_stack(plan.rows(["paperless", "authentik"]))
        assert rows["authentik"].verb == "deploy"
        assert rows["authentik"].reason == "explicit target"

    def test_a_full_plan_has_no_target_to_attribute_rows_to(self, plan, live):
        live()
        assert {row.reason for row in plan.rows(None)} == {""}
        assert {row.verb for row in plan.rows(None)} == {"deploy"}

    def test_rows_come_in_deploy_order(self, plan, live):
        live()
        assert [row.stack for row in plan.rows(["paperless"])] == [
            "reverse-proxy",
            "authentik",
            "paperless",
        ]


class TestDeployPlanReport:
    """`DeployPlan.report` — the printed plan, and what it refuses to do."""

    def test_it_prints_a_row_per_stack_with_verb_state_and_reason(self, plan, live, console):
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t1/1\n")
        assert plan.report(["paperless"]) == 0
        assert [" ".join(line.split()) for line in console.stdout] == [
            "ensure reverse-proxy converged → required by paperless",
            "ensure authentik absent → required by paperless",
            "deploy paperless absent → explicit target",
        ]

    def test_the_columns_line_up_so_the_states_can_be_scanned(self, plan, live, console):
        live()
        plan.report(["paperless"])
        assert len({line.index("→") for line in console.stdout}) == 1

    def test_the_count_goes_to_stderr_so_stdout_stays_pipeable(self, plan, live, console):
        live()
        plan.report(["paperless"])
        assert "3 stack(s) — plan only, nothing deployed." in "\n".join(console.stderr)

    def test_it_only_ever_lists(self, plan, live, commands):
        live()
        plan.report(None)
        assert [argv[:3] for argv in argvs(commands)] == [
            ["docker", "stack", "ls"],
            ["docker", "service", "ls"],
        ]

    def test_an_unresolvable_graph_exits_one_before_touching_the_cluster(
        self, plan, filesystem, console, commands
    ):
        filesystem.files["stacks/apps/ghost/docker-compose.yml"] = (
            "x-homelab:\n    requires: [nope]\nservices: {}\n"
        )
        assert plan.report(None) == 1
        assert console.stdout == []
        assert "ghost requires nope" in "\n".join(console.stderr)
        assert argvs(commands) == []

    def test_an_unreachable_cluster_exits_one_and_explains(self, plan, commands, console):
        responds(commands, CommandResult(1, "", "Cannot connect to the Docker daemon"))
        assert plan.report(None) == 1
        assert "Cannot connect to the Docker daemon" in "\n".join(console.stderr)
