"""Tests for the second-run idempotence verdict (the `ci idempotence` logic).

The pure part reads a PLAY RECAP and decides whether the second run was a no-op.
The dangerous case is a false pass: a run that failed, never reached a recap, or
touched no hosts must not read as clean. :class:`IdempotenceCheck` is driven
through a fake command runner, so both runs happen without ansible.
"""

from __future__ import annotations

import pytest

from conftest import argvs, responds

from ci.adapters import CommandResult
from ci.idempotence import parse_recap, violations

CONVERGED = """
PLAY RECAP *********************************************************************
manager-01                 : ok=42   changed=0    unreachable=0    failed=0    skipped=7    rescued=0    ignored=0
worker-01                  : ok=38   changed=0    unreachable=0    failed=0    skipped=9    rescued=0    ignored=0
"""

DRIFTED = """
PLAY RECAP *********************************************************************
manager-01                 : ok=42   changed=3    unreachable=0    failed=0    skipped=7    rescued=0    ignored=0
worker-01                  : ok=38   changed=0    unreachable=0    failed=0    skipped=9    rescued=0    ignored=0
"""


def test_parses_every_counter_for_every_host():
    recap = parse_recap(CONVERGED)
    assert set(recap) == {"manager-01", "worker-01"}
    assert recap["manager-01"]["ok"] == 42
    assert recap["manager-01"]["skipped"] == 7
    assert recap["worker-01"]["changed"] == 0


def test_converged_second_run_has_no_violations():
    assert violations(parse_recap(CONVERGED)) == {}


def test_names_only_the_host_that_changed():
    assert violations(parse_recap(DRIFTED)) == {"manager-01": "changed=3"}


@pytest.mark.parametrize(
    "counters, expected",
    [
        ("ok=1    changed=0    unreachable=1    failed=0", "unreachable=1"),
        ("ok=1    changed=0    unreachable=0    failed=2", "failed=2"),
        ("ok=1    changed=5    unreachable=0    failed=2", "failed=2"),
    ],
)
def test_a_failed_run_is_a_violation_even_with_no_changes(counters, expected):
    recap = parse_recap(f"PLAY RECAP ****\nnode-01                    : {counters}\n")
    assert violations(recap) == {"node-01": expected}


def test_ansi_coloured_output_still_parses():
    coloured = (
        "PLAY RECAP ****\n"
        "\x1b[0;32mnode-01                    : ok=3    changed=0    "
        "unreachable=0    failed=0\x1b[0m\n"
    )
    assert violations(parse_recap(coloured)) == {}


def test_trailing_output_after_the_recap_is_ignored():
    trailing = CONVERGED + "\nSunday 23 August 2026  17:03:05 -0400 (0:00:00.737)\nsome task  0.74s\n"
    assert violations(parse_recap(trailing)) == {}


def test_a_run_with_no_recap_raises_rather_than_passing():
    with pytest.raises(ValueError, match="no PLAY RECAP"):
        parse_recap("ERROR! the playbook could not be found\n")


def test_a_recap_naming_no_hosts_raises():
    with pytest.raises(ValueError, match="no hosts"):
        parse_recap("PLAY RECAP ****\n\n")


class TestIdempotenceCheck:
    """`IdempotenceCheck.verify` — runs a playbook twice and judges the second."""

    PLAYBOOK = "ansible/playbooks/bootstrap.yml"

    @pytest.fixture
    def subject(self, container):
        return container.idempotence()

    def test_a_converged_second_run_passes(self, subject, commands, console):
        responds(commands, CommandResult(0, CONVERGED), CommandResult(0, CONVERGED))
        assert subject.verify(self.PLAYBOOK) == 0
        assert "✓ second run reported no change on 2 host(s)" in console.text

    def test_the_playbook_runs_exactly_twice_with_the_same_argv(self, subject, commands):
        responds(commands, CommandResult(0, CONVERGED), CommandResult(0, CONVERGED))
        subject.verify(self.PLAYBOOK, ["-i", "inventory/"])
        expected = ["ansible-playbook", self.PLAYBOOK, "-i", "inventory/"]
        assert argvs(commands) == [expected, expected]

    def test_a_changed_second_run_fails_naming_the_host(self, subject, commands, console):
        responds(commands, CommandResult(0, CONVERGED), CommandResult(0, DRIFTED))
        assert subject.verify(self.PLAYBOOK) == 1
        assert "manager-01: changed=3" in console.text

    def test_a_failed_first_run_never_reaches_the_second(self, subject, commands, console):
        responds(commands, CommandResult(2, "boom"))
        assert subject.verify(self.PLAYBOOK) == 2
        assert len(argvs(commands)) == 1
        assert "nothing to compare" in console.text

    def test_a_second_run_with_no_recap_is_a_failure_not_a_pass(self, subject, commands, console):
        responds(commands, CommandResult(0, CONVERGED), CommandResult(0, "died early"))
        assert subject.verify(self.PLAYBOOK) == 1
        assert "did not complete" in console.text
