"""Tests for the docker CLI adapter (`ci.docker`).

Everything that knows docker exists lives here: the argv, the format templates,
and the JSON they come back as. Nothing here decides what the answers *mean* —
that is `ci.stackstate`. Every read goes through the command boundary, so these
assert the exact argv as well as the result: a plan must only ever list.
"""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest
from ci.adapters import CommandResult, CommandRunner
from ci.containers import Container
from ci.docker import Docker
from ci.stackstate import Service


def _lines(*objects: dict[str, str]) -> CommandResult:
    """Docker's `--format '{{json .}}'`: one JSON object per line, exit zero."""
    return CommandResult(0, "".join(json.dumps(o) + "\n" for o in objects))


def listed(*services: tuple[str, str]) -> CommandResult:
    """What `docker service ls` returns: (name, replicas) per service."""
    return _lines(*({"Name": n, "Replicas": r} for n, r in services))


def inspected(*services: tuple[str, str, str]) -> CommandResult:
    """What `docker service inspect` returns: (name, stack, update) per service."""
    return _lines(*({"Name": n, "Stack": s, "Update": u} for n, s, u in services))


class TestDocker:
    @pytest.fixture
    def mock_command_runner(self):
        yield Mock(spec=CommandRunner)

    @pytest.fixture
    def subject(self, container: Container, mock_command_runner: Mock) -> Docker:
        with container.override_providers(commands=mock_command_runner):
            return container.docker()

    def test_ls_returns_replicas_for_a_single_service(
        self, subject: Docker, mock_command_runner: Mock
    ):
        mock_command_runner.run.side_effect = [listed(("authentik_server", "1/1"))]

        actual = subject.ls()
        assert len(actual) == 1
        assert actual[0] == {"Name": "authentik_server", "Replicas": "1/1"}

    def test_ls_returns_replicas_for_multiple_services(
        self, subject: Docker, mock_command_runner: Mock
    ):
        mock_command_runner.run.side_effect = [
            listed(("authentik_server", "1/1"), ("authentik_worker", "1/1")),
        ]
        actual = subject.ls()
        assert len(actual) == 2
        assert actual[0] == {"Name": "authentik_server", "Replicas": "1/1"}
        assert actual[1] == {"Name": "authentik_worker", "Replicas": "1/1"}

    def test_ls_returns_empty_list_on_failure(self, subject: Docker, mock_command_runner: Mock):
        mock_command_runner.run.side_effect = [
            CommandResult(1, "failed"),
        ]
        actual = subject.ls()
        assert len(actual) == 0

    def test_inspect_returns_output_for_a_single_service(
        self, subject: Docker, mock_command_runner: Mock
    ):
        mock_command_runner.run.side_effect = [
            inspected(("authentik_server", "authentik", "none")),
        ]
        actual = subject.inspect(["authentik_server"])
        assert len(actual) == 1
        assert actual[0]["Name"] == "authentik_server"
        assert actual[0]["Stack"] == "authentik"
        assert actual[0]["Update"] == "none"

    def test_inspect_returns_output_for_multiple_services(
        self, subject: Docker, mock_command_runner: Mock
    ):
        mock_command_runner.run.side_effect = [
            inspected(
                ("authentik_server", "authentik", "none"),
                ("authentik_worker", "authentik", "none"),
            ),
        ]

        actual = subject.inspect(["authentik_server", "authentik_worker"])

        assert len(actual) == 2
        assert actual[0]["Name"] == "authentik_server"
        assert actual[1]["Name"] == "authentik_worker"
        assert {s["Stack"] for s in actual} == {"authentik"}
        assert {s["Update"] for s in actual} == {"none"}

    def test_services_reads_replicas_and_update_state(
        self, subject: Docker, mock_command_runner: Mock
    ):
        mock_command_runner.run.side_effect = [
            listed(("authentik_server", "1/1")),
            inspected(("authentik_server", "authentik", "none")),
        ]
        actual = subject.services()
        assert len(actual) == 1
        assert actual[0] == Service.from_row(
            name="authentik_server", replicas="1/1", stack="authentik", update="none"
        )

    def test_services_pairs_by_name_when_a_service_is_pruned_between_the_two_reads(
        self, subject: Docker, mock_command_runner: Mock
    ):
        """`ci plan` polls during a deploy, and `prune: true` deletes services.

        The two reads are moments apart, so `inspect` can return fewer rows than
        `ls`. Pairing them by position silently shifts every service after the
        gap into the next one's stack.
        """
        mock_command_runner.run.side_effect = [
            listed(
                ("authentik_server", "1/1"),
                ("authentik_worker", "1/1"),
                ("dns_dns-server", "1/1"),
            ),
            # authentik_worker was pruned after the listing was taken.
            inspected(
                ("authentik_server", "authentik", "none"),
                ("dns_dns-server", "dns", "none"),
            ),
        ]

        actual = subject.services()

        assert {service.name: service.stack for service in actual} == {
            "authentik_server": "authentik",
            "authentik_worker": "",
            "dns_dns-server": "dns",
        }

    def test_services_when_error_returns_empty_list(
        self, subject: Docker, mock_command_runner: Mock
    ):
        mock_command_runner.run.side_effect = [
            CommandResult(1, "failed"),
            CommandResult(1, "failed"),
        ]
        actual = subject.services()
        assert len(actual) == 0
