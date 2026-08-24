"""Tests for the configuration the CI tool reads.

`task ...` hands .env to a command via the Taskfile's ``dotenv:``; running the
CLI directly does not. :func:`merge_env` is the rule that keeps the two from
disagreeing, so it is tested directly rather than through a caller.
"""

from __future__ import annotations

import pytest

from ci.config import disabled_providers, load_env, merge_env, parse_dotenv
from conftest import ROOT, FakeFileSystem


def test_parses_a_plain_assignment():
    assert parse_dotenv("PRIMARY_DNS_MANAGED=false\n") == {"PRIMARY_DNS_MANAGED": "false"}


@pytest.mark.parametrize("line", ["KEY='v'", 'KEY="v"', "KEY=v", "  KEY = v  ", "export KEY=v"])
def test_quotes_whitespace_and_export_are_read_the_way_the_shell_reads_them(line):
    assert parse_dotenv(line) == {"KEY": "v"}


@pytest.mark.parametrize("line", ["# a comment", "", "   ", "NOT AN ASSIGNMENT", "1BAD=x"])
def test_comments_blanks_and_junk_are_ignored(line):
    assert parse_dotenv(line) == {}


def test_a_value_containing_an_equals_sign_survives():
    assert parse_dotenv("URL=a=b=c")["URL"] == "a=b=c"


def test_a_later_assignment_wins():
    assert parse_dotenv("K=1\nK=2\n") == {"K": "2"}


def test_the_process_environment_wins_over_dotenv():
    assert merge_env("K=file\n", {"K": "process"}) == {"K": "process"}


def test_dotenv_supplies_what_the_process_environment_lacks():
    assert merge_env("K=file\n", {"OTHER": "x"}) == {"K": "file", "OTHER": "x"}


def test_an_empty_dotenv_leaves_the_process_environment_alone():
    assert merge_env("", {"K": "v"}) == {"K": "v"}


def test_an_unset_gate_leaves_its_provider_enabled():
    assert disabled_providers({}) == set()


@pytest.mark.parametrize("value", ["false", "FALSE", "no", "0", "", "  false  "])
def test_a_falsey_gate_disables_its_provider(value):
    assert disabled_providers({"PRIMARY_DNS_MANAGED": value}) == {"dns"}


def test_a_truthy_gate_leaves_its_provider_enabled():
    assert disabled_providers({"PRIMARY_DNS_MANAGED": "true"}) == set()


def test_gates_can_be_supplied_explicitly():
    assert disabled_providers({"X": "false"}, gates={"thing": "X"}) == {"thing"}


def test_load_env_reads_dotenv_through_the_filesystem_port():
    fs = FakeFileSystem({".env": "K=file\n"})
    assert load_env(fs, ROOT, {})["K"] == "file"


def test_load_env_treats_a_missing_dotenv_as_empty():
    assert load_env(FakeFileSystem({}), ROOT, {"K": "v"}) == {"K": "v"}
