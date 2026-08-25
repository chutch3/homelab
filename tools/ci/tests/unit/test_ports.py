"""The fakes must satisfy the same interfaces the real adapters do.

Without this, renaming a method on a port leaves every fake behind and the suite
keeps passing against an interface that no longer exists.
"""

from __future__ import annotations

import pytest

from ci import ports
from ci.adapters import CommandResult, LocalFileSystem, Subprocess, SystemClock
from conftest import FakeFileSystem, FixedClock


@pytest.mark.parametrize(
    "port, real, fake",
    [
        (ports.FileSystem, LocalFileSystem(), FakeFileSystem()),
        (ports.Clock, SystemClock(), FixedClock()),
    ],
)
def test_the_fake_and_the_real_adapter_satisfy_the_same_port(port, real, fake):
    assert isinstance(real, port)
    assert isinstance(fake, port)


def test_the_subprocess_adapter_satisfies_the_command_runner_port():
    assert isinstance(Subprocess(), ports.CommandRunner)


def test_a_command_result_satisfies_the_outcome_port():
    assert isinstance(CommandResult(0), ports.CommandOutcome)


def test_an_object_missing_a_port_method_does_not_satisfy_it():
    class Partial:
        def glob(self, root, pattern):
            return []

    assert not isinstance(Partial(), ports.FileSystem)
