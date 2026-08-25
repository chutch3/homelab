"""Tests for `ci.deploy.DeployPlanner` — resolved order plus live cluster state.

A plan is only useful if it says what will happen rather than listing
everything, so the assertions here are about the two things that distinguish
the rows: the state each stack is already in, and why it is in the plan at all.
"""

from __future__ import annotations

import json

import pytest

from conftest import argvs, responds

from ci.adapters import CommandResult
from ci.cluster import StackState
from ci.deploy import Action, Origin, PlanRow

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

    def test_rows_a_target_pulls_in_its_chain_each_carrying_its_live_state(
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

    def test_rows_a_shared_dependency_names_every_target_that_needs_it(
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

    def test_rows_a_full_plan_has_no_target_to_attribute_rows_to(self, subject, live):
        live()
        assert subject.rows(None) == [
            PlanRow("reverse-proxy", StackState.ABSENT, Origin.WHOLE_TREE),
            PlanRow("authentik", StackState.ABSENT, Origin.WHOLE_TREE),
            PlanRow("paperless", StackState.ABSENT, Origin.WHOLE_TREE),
        ]

    def test_rows_reads_the_tree_once_though_it_asks_the_graph_twice(
        self, subject, live, filesystem
    ):
        """Order and attribution are two questions; the compose files answer both."""
        live()
        subject.rows(["paperless"])
        assert len(filesystem.reads) == len(TREE)

    # --- what each row will actually do -------------------------------------

    def test_rows_a_converged_dependency_is_skipped_so_its_spec_is_never_touched(
        self, subject, live
    ):
        """Deploying paperless must not restart authentik."""
        live(
            stacks="reverse-proxy\nauthentik\n",
            services="reverse-proxy_traefik\t1/1\nauthentik_server\t1/1\n",
        )
        assert [(r.stack, r.action) for r in subject.rows(["paperless"])] == [
            ("reverse-proxy", Action.SKIP),
            ("authentik", Action.SKIP),
            ("paperless", Action.DEPLOY),
        ]

    def test_rows_a_dependency_short_of_converged_is_deployed(self, subject, live):
        live(stacks="authentik\n", services="authentik_server\t0/1\n")
        assert [(r.stack, r.action) for r in subject.rows(["paperless"])] == [
            ("reverse-proxy", Action.DEPLOY),
            ("authentik", Action.DEPLOY),
            ("paperless", Action.DEPLOY),
        ]

    def test_rows_an_explicit_target_deploys_even_when_already_converged(
        self, subject, live
    ):
        live(stacks="paperless\n", services="paperless_web\t1/1\n")
        assert [r for r in subject.rows(["paperless"]) if r.stack == "paperless"][0].action is (
            Action.DEPLOY
        )

    def test_rows_a_full_plan_over_a_converged_cluster_has_nothing_to_do(
        self, subject, live
    ):
        """The resume: a re-run from the top redeploys nothing it already converged."""
        live(
            stacks="reverse-proxy\nauthentik\npaperless\n",
            services=(
                "reverse-proxy_traefik\t1/1\nauthentik_server\t1/1\npaperless_web\t1/1\n"
            ),
        )
        assert [r.action for r in subject.rows(None)] == [Action.SKIP] * 3

    # --- the plan it prints --------------------------------------------------

    def test_report_leads_each_row_with_what_will_happen_to_it(
        self, subject, live, capsys
    ):
        """One column says what the run does, the other why the row is here."""
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t1/1\n")
        assert subject.report(["paperless"]) == 0
        assert [" ".join(line.split()) for line in capsys.readouterr().out.splitlines()] == [
            "skip reverse-proxy converged → required by paperless",
            "deploy authentik absent → required by paperless",
            "deploy paperless absent → explicit target",
        ]

    def test_report_a_full_plan_skips_what_has_converged_and_names_no_cause(
        self, subject, live, capsys
    ):
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t1/1\n")
        assert subject.report(None) == 0
        assert [" ".join(line.split()) for line in capsys.readouterr().out.splitlines()] == [
            "skip reverse-proxy converged",
            "deploy authentik absent",
            "deploy paperless absent",
        ]

    def test_report_aligns_the_columns_so_the_states_can_be_scanned(self, subject, live, capsys):
        live()
        subject.report(["paperless"])
        assert len({line.index("→") for line in capsys.readouterr().out.splitlines()}) == 1

    def test_report_logs_the_count_so_stdout_carries_only_the_plan(
        self, subject, live, capsys, caplog
    ):
        live()
        subject.report(["paperless"])
        assert "3 stack(s), 3 to deploy — plan only, nothing deployed." in caplog.text
        assert "stack(s)" not in capsys.readouterr().out

    def test_report_a_target_this_environment_switched_off_fails_rather_than_no_ops(
        self, container, filesystem, env, live, capsys, caplog
    ):
        """Exiting 0 would tell a caller its stack was handled, not discarded."""
        filesystem.files.update({**TREE, "stacks/dns/docker-compose.yml": PROXY})
        env["PRIMARY_DNS_MANAGED"] = "false"
        live()
        assert container.planner().report(["dns"]) == 1
        assert capsys.readouterr().out == ""
        assert "dns" in caplog.text and "switched off" in caplog.text

    def test_report_a_switched_off_target_alongside_a_live_one_still_fails(
        self, container, filesystem, env, live, capsys, caplog
    ):
        """The plan is non-empty, so only naming the dropped target catches this."""
        filesystem.files.update({**TREE, "stacks/dns/docker-compose.yml": PROXY})
        env["PRIMARY_DNS_MANAGED"] = "false"
        live()
        assert container.planner().report(["dns", "paperless"]) == 1
        assert capsys.readouterr().out == ""
        assert "dns" in caplog.text and "paperless" not in caplog.text

    def test_report_a_whole_tree_plan_over_an_empty_repo_is_not_an_error(
        self, subject, filesystem, live, capsys
    ):
        """Nothing asked for and nothing found is empty, not wrong."""
        filesystem.files.clear()
        live()
        assert subject.report(None) == 0
        assert capsys.readouterr().out == ""

    def test_report_as_json_emits_the_deploy_order_the_playbook_loops_over(
        self, subject, live, capsys
    ):
        """Three fields, all of them read: the playbook deploys, skips, and reports."""
        live(stacks="reverse-proxy\n", services="reverse-proxy_traefik\t1/1\n")
        assert subject.report(["paperless"], as_json=True) == 0
        assert json.loads(capsys.readouterr().out) == [
            {"stack": "reverse-proxy", "state": "converged", "action": "skip"},
            {"stack": "authentik", "state": "absent", "action": "deploy"},
            {"stack": "paperless", "state": "absent", "action": "deploy"},
        ]

    def test_report_as_json_stays_silent_on_stdout_when_the_graph_is_broken(
        self, subject, filesystem, capsys
    ):
        """A parse of half a plan is worse than none, so stdout carries nothing."""
        filesystem.files["stacks/apps/ghost/docker-compose.yml"] = (
            "x-homelab:\n    requires: [nope]\nservices: {}\n"
        )
        assert subject.report(None, as_json=True) == 1
        assert capsys.readouterr().out == ""

    def test_report_only_ever_lists_the_cluster(self, subject, live, commands):
        live()
        subject.report(None)
        assert [argv[:3] for argv in argvs(commands)] == [
            ["docker", "stack", "ls"],
            ["docker", "service", "ls"],
        ]

    def test_report_an_unresolvable_graph_exits_one_before_touching_the_cluster(
        self, subject, filesystem, capsys, caplog, commands
    ):
        filesystem.files["stacks/apps/ghost/docker-compose.yml"] = (
            "x-homelab:\n    requires: [nope]\nservices: {}\n"
        )
        assert subject.report(None) == 1
        assert capsys.readouterr().out == ""
        assert "ghost requires nope" in caplog.text
        assert argvs(commands) == []

    def test_report_an_unreachable_cluster_exits_one_and_explains(self, subject, commands, caplog):
        responds(commands, CommandResult(1, "", "Cannot connect to the Docker daemon"))
        assert subject.report(None) == 1
        assert "Cannot connect to the Docker daemon" in caplog.text
