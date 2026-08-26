"""Tests for the stack tree invariants (`ci check-stacks`).

One verdict over the whole tree: the declarations resolve and are complete, and
every stack says when it is ready. The dangerous case is a check that passes
because its scope was drawn around the things already compliant, so the
healthcheck rule is asserted against the real tree as well as fakes.
"""

from __future__ import annotations

import pytest

from conftest import FakeFileSystem

from ci.stackcheck import RATCHET_FILE, check_stacks, parse_ratchet

HEALTHY = 'services:\n    a:\n        healthcheck:\n            test: ["CMD", "true"]\n'
BARE = "services:\n    a:\n        image: alpine\n"
TRAEFIK_LABEL = 'services:\n    a:\n        deploy:\n            labels: ["traefik.enable=true"]\n'
DECLARED = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK_LABEL


def tree(filesystem: FakeFileSystem, **stacks: str) -> None:
    filesystem.files.update(
        {f"stacks/apps/{name}/docker-compose.yml": text for name, text in stacks.items()}
    )


def ratchet(filesystem: FakeFileSystem, *names: str) -> None:
    body = "".join(f"  - {name}\n" for name in names) or "  []\n"
    filesystem.files[RATCHET_FILE] = f"without_healthcheck:\n{body}"


def check(container) -> int:
    return check_stacks(container.stack_tree(), container.graph(), container.ratchet())


# ── the verdict ──────────────────────────────────────────────────────────────

def test_check_stacks_passes_a_tree_that_resolves_declares_and_reports_readiness(
    container, filesystem, caplog
):
    tree(filesystem, paperless=DECLARED, **{"reverse-proxy": HEALTHY})
    ratchet(filesystem, "paperless")
    assert check(container) == 0
    assert "✓ 2 stacks" in caplog.text


def test_check_stacks_names_the_stack_hiding_an_undeclared_dependency(
    container, filesystem, caplog
):
    tree(filesystem, komga=TRAEFIK_LABEL, **{"reverse-proxy": HEALTHY})
    ratchet(filesystem, "komga")
    assert check(container) == 1
    assert "    komga: reverse-proxy" in caplog.text


def test_check_stacks_fails_on_an_unresolvable_graph_before_looking_for_gaps(
    container, filesystem, caplog
):
    tree(filesystem, gamarr="x-homelab:\n    requires: [romm]\nservices: {}\n")
    ratchet(filesystem)
    assert check(container) == 1
    assert "gamarr requires romm" in caplog.text


def test_check_stacks_explains_the_shape_of_a_malformed_declaration(
    container, filesystem, caplog
):
    tree(filesystem, paperless="x-homelab:\n    requires: reverse-proxy\nservices: {}\n")
    ratchet(filesystem)
    assert check(container) == 1
    assert "x-homelab.requires must be a list" in caplog.text


def test_check_stacks_reads_each_compose_file_once_however_many_rules_run(
    container, filesystem
):
    tree(filesystem, paperless=DECLARED, **{"reverse-proxy": HEALTHY})
    ratchet(filesystem, "paperless")
    check(container)
    composes = [read for read in filesystem.reads if read.endswith("docker-compose.yml")]
    assert sorted(composes) == sorted(set(composes))
    assert len(composes) == 2


# ── the healthcheck rule ─────────────────────────────────────────────────────

def test_check_stacks_names_a_stack_with_no_healthcheck(container, filesystem, caplog):
    tree(filesystem, newcomer=BARE)
    ratchet(filesystem)
    assert check(container) == 1
    assert "newcomer" in caplog.text


def test_check_stacks_accepts_one_service_with_a_healthcheck_out_of_several(container, filesystem):
    tree(filesystem, newcomer=HEALTHY + "    b:\n        image: alpine\n")
    ratchet(filesystem)
    assert check(container) == 0


def test_check_stacks_names_every_offender_not_just_the_first(container, filesystem, caplog):
    tree(filesystem, one=BARE, two=BARE)
    ratchet(filesystem)
    assert check(container) == 1
    assert "one" in caplog.text and "two" in caplog.text


def test_check_stacks_lets_a_stack_on_the_ratchet_lack_a_healthcheck(container, filesystem):
    """The baseline is the debt that exists today; it fails only when it grows."""
    tree(filesystem, legacy=BARE)
    ratchet(filesystem, "legacy")
    assert check(container) == 0


def test_check_stacks_still_fails_a_stack_the_ratchet_does_not_name(
    container, filesystem, caplog
):
    tree(filesystem, legacy=BARE, newcomer=BARE)
    ratchet(filesystem, "legacy")
    assert check(container) == 1
    assert "newcomer" in caplog.text and "    legacy" not in caplog.text


# ── the ratchet file ─────────────────────────────────────────────────────────

def test_parse_ratchet_reads_the_names_it_lists():
    assert parse_ratchet("without_healthcheck:\n  - komga\n  - radarr\n") == {"komga", "radarr"}


def test_parse_ratchet_treats_an_absent_or_empty_file_as_no_exemptions():
    assert parse_ratchet("") == frozenset()
    assert parse_ratchet("without_healthcheck:\n") == frozenset()


@pytest.mark.parametrize("text", ["without_healthcheck: komga\n", "without_healthcheck:\n  - [x]\n"])
def test_parse_ratchet_refuses_anything_that_is_not_a_list_of_names(text):
    with pytest.raises(ValueError, match="without_healthcheck"):
        parse_ratchet(text)


# ── this repo ────────────────────────────────────────────────────────────────

def test_the_real_tree_passes_every_invariant(repo_container):
    assert check_stacks(
        repo_container.stack_tree(), repo_container.graph(), repo_container.ratchet()
    ) == 0


def test_the_ratchet_names_no_stack_that_has_since_gained_a_healthcheck(repo_container):
    """A name left on the list after the fact hides the next regression."""
    stacks = repo_container.stack_tree().stacks()
    stale = {n for n in repo_container.ratchet() if n in stacks and stacks[n].has_healthcheck}
    assert stale == set(), f"remove from {RATCHET_FILE}: {sorted(stale)}"


def test_the_ratchet_names_no_stack_that_no_longer_exists(repo_container):
    gone = repo_container.ratchet() - set(repo_container.stack_tree().stacks())
    assert gone == set(), f"remove from {RATCHET_FILE}: {sorted(gone)}"
