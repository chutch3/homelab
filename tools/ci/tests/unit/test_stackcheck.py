"""Tests for the stack tree invariants (`ci check-stacks`).

One verdict over the whole tree: the declarations resolve and are complete, and
every stack says when it is ready. The dangerous case is a check that passes
because its scope was drawn around the things already compliant, so the
healthcheck rule is asserted against the real tree as well as fakes.
"""

from __future__ import annotations

import pytest

from conftest import ROOT, FakeFileSystem

from ci.stackcheck import WITHOUT_HEALTHCHECK, check_stacks

HEALTHY = 'services:\n    a:\n        healthcheck:\n            test: ["CMD", "true"]\n'
BARE = "services:\n    a:\n        image: alpine\n"
TRAEFIK_LABEL = 'services:\n    a:\n        deploy:\n            labels: ["traefik.enable=true"]\n'
DECLARED = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK_LABEL


def tree(filesystem: FakeFileSystem, **stacks: str) -> None:
    filesystem.files.update(
        {f"stacks/apps/{name}/docker-compose.yml": text for name, text in stacks.items()}
    )


class TestCheckStacks:
    """`check_stacks` — the single verdict `ci check-stacks` prints."""

    def test_a_tree_that_resolves_declares_and_reports_readiness_passes(
        self, container, filesystem, caplog
    ):
        tree(filesystem, paperless=DECLARED + HEALTHY.replace("services:\n", ""),
             **{"reverse-proxy": HEALTHY})
        assert check_stacks(container.graph()) == 0

    def test_an_undeclared_dependency_is_named(self, container, filesystem, caplog):
        tree(filesystem, komga=TRAEFIK_LABEL, **{"reverse-proxy": HEALTHY})
        assert check_stacks(container.graph()) == 1
        assert "komga: reverse-proxy" in caplog.text

    def test_an_unresolvable_graph_fails_before_looking_any_further(
        self, container, filesystem, caplog
    ):
        tree(filesystem, gamarr="x-homelab:\n    requires: [romm]\nservices: {}\n")
        assert check_stacks(container.graph()) == 1
        assert "gamarr requires romm" in caplog.text

    def test_a_stack_with_no_healthcheck_is_named(self, container, filesystem, caplog):
        tree(filesystem, newcomer=BARE)
        assert check_stacks(container.graph()) == 1
        assert "newcomer" in caplog.text

    def test_one_healthchecked_service_is_enough(self, container, filesystem):
        tree(filesystem, newcomer=HEALTHY + "    b:\n        image: alpine\n")
        assert check_stacks(container.graph()) == 0

    def test_a_stack_on_the_ratchet_may_still_lack_one(self, container, filesystem):
        """The baseline is the debt that exists today; it fails only when it grows."""
        listed = sorted(WITHOUT_HEALTHCHECK)[0]
        tree(filesystem, **{listed: BARE})
        assert check_stacks(container.graph()) == 0

    def test_a_stack_not_on_the_ratchet_may_not(self, container, filesystem, caplog):
        tree(filesystem, brand_new_stack=BARE)
        assert check_stacks(container.graph()) == 1
        assert "brand_new_stack" in caplog.text

    def test_every_offender_is_named_not_just_the_first(self, container, filesystem, caplog):
        tree(filesystem, one=BARE, two=BARE)
        assert check_stacks(container.graph()) == 1
        assert "one" in caplog.text and "two" in caplog.text


class TestThisRepo:
    """The tree itself, against the real filesystem."""

    @pytest.fixture
    def subject(self, repo_container):
        return repo_container.graph()

    def test_the_real_tree_passes_every_invariant(self, subject):
        assert check_stacks(subject) == 0

    def test_the_ratchet_names_no_stack_that_has_since_gained_a_healthcheck(self, subject):
        """A name left on the list after the fact hides the next regression."""
        stale = {
            name
            for name, stack in subject.stacks().items()
            if name in WITHOUT_HEALTHCHECK and stack.healthchecked
        }
        assert stale == set(), f"remove from WITHOUT_HEALTHCHECK: {sorted(stale)}"

    def test_the_ratchet_names_no_stack_that_no_longer_exists(self, subject):
        assert WITHOUT_HEALTHCHECK - set(subject.stacks()) == set()
