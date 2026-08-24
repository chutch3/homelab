"""Tests for `ci.deploy.DeployPlanner` — resolved order plus live cluster state.

A plan is only useful if it says what will happen rather than listing
everything, so the assertions here are about the two things that distinguish
the rows: the state each stack is already in, and why it is in the plan at all.
"""

from __future__ import annotations

import pytest

from conftest import argvs, responds

from ci.adapters import CommandResult
from ci.cluster import StackState
from ci.deploy import Origin, PlanRow

LABELS = 'services:\n    a:\n        deploy:\n            labels: [{}]\n'
TRAEFIK = LABELS.format('"traefik.enable=true"')
PROXY = "services: {}\n"
NEEDS_PROXY = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK
NEEDS_AUTH = "x-homelab:\n    requires: [reverse-proxy, authentik]\n" + LABELS.format(
    '"traefik.enable=true", "traefik.http.routers.p.middlewares=authentik@swarm"'
)

# paperless → authentik → reverse-proxy, so one target exercises a transitive edge.
TREE = {
    "stacks/reverse-proxy/docker-compose.yml": PROXY,
    "stacks/apps/authentik/docker-compose.yml": NEEDS_PROXY,
    "stacks/apps/paperless/docker-compose.yml": NEEDS_AUTH,
}


class TestDeployPlanner:
    """`DeployPlanner` — the plan it builds, and the plan it prints."""

    @pytest.fixture
    def subject(self, container, filesystem):
        filesystem.files.update(TREE)
        return container.planner()

    @pytest.fixture
    def live(self, commands):
        """Seed what the cluster reports: stack names, then `service<TAB>replicas`."""

        def _live(stacks: str = "", services: str = "") -> None:
            responds(commands, CommandResult(0, stacks), CommandResult(0, services))

        return _live

    # --- the plan it builds -------------------------------------------------

    def test_a_target_pulls_in_its_chain_each_row_carrying_its_live_state(
        self, subject, live
    ):
        """One assertion for the whole plan: order, state, and why each row is there."""
        live(
            stacks="reverse-proxy\nauthentik\n",
            services="reverse-proxy_traefik\t1/1\nauthentik_server\t0/1\n",
        )
        assert subject.rows(["paperless"]) == [
            PlanRow("reverse-proxy", StackState.CONVERGED, Origin.DEPENDENCY, ("paperless",)),
            PlanRow("authentik", StackState.PRESENT, Origin.DEPENDENCY, ("paperless",)),
            PlanRow("paperless", StackState.ABSENT, Origin.TARGET),
        ]

    def test_a_shared_dependency_names_every_target_and_a_named_target_stays_one(
        self, subject, live
    ):
        live()
        assert subject.rows(["paperless", "authentik"]) == [
            PlanRow(
                "reverse-proxy",
                StackState.ABSENT,
                Origin.DEPENDENCY,
                ("authentik", "paperless"),
            ),
            PlanRow("authentik", StackState.ABSENT, Origin.TARGET),
            PlanRow("paperless", StackState.ABSENT, Origin.TARGET),
        ]

    def test_a_full_plan_has_no_target_to_attribute_rows_to(self, subject, live):
        live()
        assert subject.rows(None) == [
            PlanRow("reverse-proxy", StackState.ABSENT, Origin.WHOLE_TREE),
            PlanRow("authentik", StackState.ABSENT, Origin.WHOLE_TREE),
            PlanRow("paperless", StackState.ABSENT, Origin.WHOLE_TREE),
        ]

    def test_it_reads_the_tree_once_though_it_asks_the_graph_twice(
        self, subject, live, filesystem
    ):
        """Order and attribution are two questions; the compose files answer both."""
        live()
        subject.rows(["paperless"])
        assert len(filesystem.reads) == len(TREE)

    # --- the plan it prints --------------------------------------------------

    def test_it_prints_a_row_per_stack_with_verb_state_and_reason(self, subject, live, capsys):
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t1/1\n")
        assert subject.report(["paperless"]) == 0
        assert [" ".join(line.split()) for line in capsys.readouterr().out.splitlines()] == [
            "ensure reverse-proxy converged → required by paperless",
            "ensure authentik absent → required by paperless",
            "deploy paperless absent → explicit target",
        ]

    def test_the_columns_line_up_so_the_states_can_be_scanned(self, subject, live, capsys):
        live()
        subject.report(["paperless"])
        assert len({line.index("→") for line in capsys.readouterr().out.splitlines()}) == 1

    def test_the_count_is_logged_so_stdout_carries_only_the_plan(
        self, subject, live, capsys, caplog
    ):
        live()
        subject.report(["paperless"])
        assert "3 stack(s) — plan only, nothing deployed." in caplog.text
        assert "stack(s)" not in capsys.readouterr().out

    def test_it_only_ever_lists(self, subject, live, commands):
        live()
        subject.report(None)
        assert [argv[:3] for argv in argvs(commands)] == [
            ["docker", "stack", "ls"],
            ["docker", "service", "ls"],
        ]

    def test_an_unresolvable_graph_exits_one_before_touching_the_cluster(
        self, subject, filesystem, capsys, caplog, commands
    ):
        filesystem.files["stacks/apps/ghost/docker-compose.yml"] = (
            "x-homelab:\n    requires: [nope]\nservices: {}\n"
        )
        assert subject.report(None) == 1
        assert capsys.readouterr().out == ""
        assert "ghost requires nope" in caplog.text
        assert argvs(commands) == []

    def test_an_unreachable_cluster_exits_one_and_explains(self, subject, commands, caplog):
        responds(commands, CommandResult(1, "", "Cannot connect to the Docker daemon"))
        assert subject.report(None) == 1
        assert "Cannot connect to the Docker daemon" in caplog.text
