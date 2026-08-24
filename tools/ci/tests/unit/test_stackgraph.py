"""Tests for the stack dependency graph (`ci deploy --plan` / `ci check-deps`).

The dangerous case is a false pass: an order that puts a stack before something
it needs, or a declaration the tree does not actually satisfy. `resolve` and
`cycle_members` are functions over plain mappings and are tested as such;
everything that would read the tree goes through a fake filesystem.
"""

from __future__ import annotations

import pytest
from dependency_injector import providers

from ci.stackgraph import (
    Stack,
    StackTree,
    UnresolvedGraph,
    check_dependencies,
    cycle_members,
    required_by,
    resolve,
)
from conftest import ROOT, FakeFileSystem

ROUTED = {
    "reverse-proxy": [],
    "authentik": ["reverse-proxy"],
    "paperless": ["reverse-proxy", "authentik"],
}

TRAEFIK_LABEL = 'services:\n    a:\n        deploy:\n            labels: ["traefik.enable=true"]\n'
DECLARED = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK_LABEL
CYCLE = {"authentik": ["paperless"], "paperless": ["authentik"], "komga": ["authentik"]}


def compose(**stacks: str) -> dict[str, str]:
    """Seed a fake tree: stack name -> compose text, all under stacks/apps/."""
    return {f"stacks/apps/{name}/docker-compose.yml": text for name, text in stacks.items()}


def test_resolve_orders_every_stack_after_its_dependencies():
    order = resolve(ROUTED)
    assert order.index("reverse-proxy") < order.index("authentik") < order.index("paperless")


def test_resolve_orders_the_whole_tree_when_no_targets_are_named():
    assert set(resolve(ROUTED)) == set(ROUTED)


def test_resolve_pulls_in_only_a_targets_own_dependencies():
    assert resolve(ROUTED, targets=["authentik"]) == ["reverse-proxy", "authentik"]


def test_resolve_orders_independent_stacks_alphabetically():
    assert resolve({"beta": [], "alpha": [], "gamma": []}) == ["alpha", "beta", "gamma"]


def test_resolve_is_deterministic():
    graph = {"d": ["a"], "c": ["a"], "b": ["c", "d"], "a": []}
    assert resolve(graph) == resolve(graph)


def test_resolve_fails_naming_both_ends_of_a_dependency_that_does_not_exist():
    with pytest.raises(UnresolvedGraph) as exc:
        resolve({"paperless": ["ghost-stack"]})
    assert "paperless requires ghost-stack" in str(exc.value)


def test_resolve_fails_naming_a_target_that_does_not_exist():
    with pytest.raises(UnresolvedGraph, match="no such stack: ghost-stack"):
        resolve(ROUTED, targets=["ghost-stack"])


def test_resolve_drops_a_disabled_stack_and_the_edges_into_it():
    assert resolve({"dns": [], "paperless": ["dns"]}, disabled=["dns"]) == ["paperless"]


def test_resolve_drops_a_disabled_stack_even_when_it_is_the_target():
    order = resolve({"dns": [], "paperless": ["dns"]}, targets=["dns", "paperless"], disabled=["dns"])
    assert order == ["paperless"]


def test_resolve_reports_a_cycle_naming_its_members_and_nothing_else():
    with pytest.raises(UnresolvedGraph) as exc:
        resolve(CYCLE)
    assert str(exc.value) == "dependency cycle among: authentik, paperless"


def test_resolve_treats_a_stack_requiring_itself_as_a_cycle():
    with pytest.raises(UnresolvedGraph) as exc:
        resolve({"loop": ["loop"]})
    assert str(exc.value) == "dependency cycle among: loop"


def test_required_by_attributes_a_dependency_to_the_target_that_named_it():
    assert required_by(ROUTED, ["paperless"])["authentik"] == ["paperless"]


def test_required_by_attributes_a_transitive_dependency_to_the_target_not_the_middle():
    assert required_by(ROUTED, ["paperless"])["reverse-proxy"] == ["paperless"]


def test_required_by_names_every_target_that_reaches_a_shared_dependency():
    assert required_by(ROUTED, ["paperless", "authentik"])["reverse-proxy"] == [
        "authentik",
        "paperless",
    ]


def test_required_by_never_makes_a_target_its_own_dependency():
    assert "paperless" not in required_by(ROUTED, ["paperless"])


def test_required_by_ignores_a_disabled_stack_and_the_edges_into_it():
    graph = {"dns": [], "reverse-proxy": ["dns"], "paperless": ["reverse-proxy"]}
    assert required_by(graph, ["paperless"], disabled=["dns"]) == {"reverse-proxy": ["paperless"]}


def test_required_by_rejects_a_dangling_edge_exactly_as_resolve_does():
    """Both walk the same declarations, so both must refuse the same broken ones."""
    with pytest.raises(UnresolvedGraph, match="paperless requires ghost-stack"):
        required_by({"paperless": ["ghost-stack"]}, ["paperless"])


def test_required_by_rejects_a_target_that_does_not_exist():
    with pytest.raises(UnresolvedGraph, match="no such stack: ghost-stack"):
        required_by(ROUTED, ["ghost-stack"])


def test_required_by_survives_a_cycle_rather_than_looping_forever():
    assert required_by(CYCLE, ["komga"]) == {"authentik": ["komga"], "paperless": ["komga"]}


def test_cycle_members_names_only_the_cycle_not_the_stacks_it_blocks():
    assert cycle_members(CYCLE, sorted(CYCLE)) == ["authentik", "paperless"]


class TestStack:
    """`Stack` — what a compose file gives away about its own dependencies."""

    def _stack(self, name: str, text: str, requires: tuple[str, ...] = ()) -> Stack:
        return Stack(name, ROOT / name / "docker-compose.yml", text, requires)

    def test_a_traefik_router_implies_the_reverse_proxy(self):
        assert self._stack("paperless", TRAEFIK_LABEL).inferred == {"reverse-proxy"}

    def test_no_traefik_router_implies_nothing(self):
        assert self._stack("kopia", "image: kopia/kopia").inferred == set()

    def test_a_forward_auth_middleware_implies_authentik(self):
        text = '- "traefik.http.routers.tor.middlewares=authentik@swarm"'
        assert self._stack("tor-browser", text).inferred == {"authentik"}

    def test_an_oidc_issuer_on_the_auth_host_implies_authentik(self):
        text = "- OIDC_CONFIGURATION_URL=https://auth.${BASE_DOMAIN}/x"
        assert self._stack("mealie", text).inferred == {"authentik"}

    def test_a_stack_never_infers_a_dependency_on_itself(self):
        text = TRAEFIK_LABEL + "\n- AUTHENTIK_HOST=https://auth.${BASE_DOMAIN}"
        assert self._stack("authentik", text).inferred == {"reverse-proxy"}
        assert self._stack("reverse-proxy", text).inferred == {"authentik"}

    def test_undeclared_is_what_it_reveals_minus_what_it_declares(self):
        stack = self._stack("paperless", TRAEFIK_LABEL, requires=("reverse-proxy",))
        assert stack.undeclared == set()

    def test_undeclared_names_the_gap(self):
        text = TRAEFIK_LABEL + '\n- "traefik.http.routers.p.middlewares=authentik@swarm"'
        stack = self._stack("paperless", text, requires=("reverse-proxy",))
        assert stack.undeclared == {"authentik"}


class TestStackTree:
    """`StackTree` — reading and validating the declarations off the filesystem."""

    @pytest.fixture
    def subject(self, filesystem):
        return StackTree(filesystem, ROOT)

    def _seed(self, filesystem: FakeFileSystem, **stacks: str) -> None:
        filesystem.files.update(compose(**stacks))

    def test_reads_the_declared_requires(self, subject, filesystem):
        self._seed(filesystem, paperless=DECLARED)
        assert subject.stacks()["paperless"].requires == ("reverse-proxy",)

    def test_a_stack_declaring_nothing_has_no_requires(self, subject, filesystem):
        self._seed(filesystem, flaresolverr="services:\n    a:\n        image: x\n")
        assert subject.stacks()["flaresolverr"].requires == ()

    def test_reads_both_stack_roots(self, subject, filesystem):
        filesystem.files.update(
            {
                "stacks/monitoring/docker-compose.yml": DECLARED,
                "stacks/apps/paperless/docker-compose.yml": DECLARED,
            }
        )
        assert set(subject.stacks()) == {"monitoring", "paperless"}

    def test_each_compose_file_is_read_exactly_once(self, subject, filesystem):
        self._seed(filesystem, paperless=DECLARED, komga=DECLARED, kopia=DECLARED)
        subject.stacks()
        assert sorted(filesystem.reads) == sorted(set(filesystem.reads))
        assert len(filesystem.reads) == 3

    def test_stacks_asking_again_does_not_re_read_the_tree(self, subject, filesystem):
        """Callers ask several questions of one tree; the disk is read for the first."""
        self._seed(filesystem, paperless=DECLARED, komga=DECLARED, kopia=DECLARED)
        subject.stacks()
        subject.stacks()
        subject.stacks()
        assert len(filesystem.reads) == 3

    def test_a_name_used_in_both_roots_fails_rather_than_shadowing(self, subject, filesystem):
        filesystem.files.update(
            {
                "stacks/dns/docker-compose.yml": DECLARED,
                "stacks/apps/dns/docker-compose.yml": DECLARED,
            }
        )
        with pytest.raises(UnresolvedGraph, match="two stacks named dns"):
            subject.stacks()

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("x-homelab:\n    requires: reverse-proxy\nservices: {}\n", "must be a list"),
            ("x-homelab:\n    requires: [{a: b}]\nservices: {}\n", "must be stack names"),
            ("x-homelab: [reverse-proxy]\nservices: {}\n", "must be a mapping"),
            ("services: [\n  unclosed\n", "not valid YAML"),
            ("- just\n- a list\n", "not a mapping"),
        ],
    )
    def test_a_malformed_declaration_fails_naming_the_stack_and_the_problem(
        self, subject, filesystem, text, expected
    ):
        self._seed(filesystem, paperless=text)
        with pytest.raises(UnresolvedGraph) as exc:
            subject.stacks()
        assert str(exc.value).startswith("paperless: ")
        assert expected in str(exc.value)


class TestDependencyGraph:
    """`DependencyGraph` — the graph over the tree, and the capability gates."""

    @pytest.fixture
    def subject(self, container):
        return container.graph()

    def _seed(self, filesystem: FakeFileSystem, **stacks: str) -> None:
        filesystem.files.update(compose(**stacks))

    def test_edges_are_the_declarations(self, subject, filesystem):
        self._seed(filesystem, paperless=DECLARED, **{"reverse-proxy": TRAEFIK_LABEL})
        assert subject.edges() == {"paperless": ["reverse-proxy"], "reverse-proxy": []}

    def test_undeclared_reports_only_the_stacks_with_a_gap(self, subject, filesystem):
        self._seed(filesystem, paperless=DECLARED, komga=TRAEFIK_LABEL)
        assert subject.undeclared() == {"komga": {"reverse-proxy"}}

    def test_resolves_in_dependency_order(self, subject, filesystem):
        self._seed(filesystem, paperless=DECLARED, **{"reverse-proxy": "services: {}\n"})
        assert subject.resolve() == ["reverse-proxy", "paperless"]

    def test_a_target_pulls_in_its_dependencies(self, subject, filesystem):
        self._seed(filesystem, paperless=DECLARED, komga=DECLARED,
                   **{"reverse-proxy": "services: {}\n"})
        assert subject.resolve(["paperless"]) == ["reverse-proxy", "paperless"]

    def test_no_gate_set_leaves_every_provider_enabled(self, subject, filesystem):
        self._seed(filesystem, dns="services: {}\n")
        assert subject.disabled() == set()
        assert subject.resolve() == ["dns"]

    @pytest.mark.parametrize("value", ["false", "FALSE", "no", "0", ""])
    def test_a_falsey_gate_drops_its_provider_and_the_edges_into_it(
        self, container, filesystem, value
    ):
        self._seed(filesystem, dns="services: {}\n",
                   paperless="x-homelab:\n    requires: [dns]\nservices: {}\n")
        container.env.override(providers.Object({"PRIMARY_DNS_MANAGED": value}))
        subject = container.graph()
        assert subject.disabled() == {"dns"}
        assert subject.resolve() == ["paperless"]

    def test_a_truthy_gate_keeps_its_provider(self, container, filesystem):
        self._seed(filesystem, dns="services: {}\n")
        container.env.override(providers.Object({"PRIMARY_DNS_MANAGED": "true"}))
        assert container.graph().disabled() == set()


class TestThisRepo:
    """The declarations in the tree itself, against the real filesystem."""

    @pytest.fixture
    def subject(self, repo_container):
        return repo_container.graph()

    def test_every_stack_in_the_tree_resolves_in_dependency_order(self, subject):
        order = subject.resolve()
        assert len(order) == len(subject.stacks()) - len(subject.disabled())
        for stack, requires in subject.edges().items():
            if stack in subject.disabled():
                continue
            for dependency in requires:
                if dependency not in subject.disabled():
                    assert order.index(dependency) < order.index(stack)

    def test_every_dependency_the_tree_reveals_is_declared(self, subject):
        assert subject.undeclared() == {}


def _tree(filesystem: FakeFileSystem, **stacks: str) -> None:
    filesystem.files.update(compose(**stacks))


def test_check_dependencies_passes_a_tree_that_resolves_and_declares_everything(
    container, filesystem, caplog
):
    _tree(filesystem, paperless=DECLARED, **{"reverse-proxy": "services: {}\n"})
    assert check_dependencies(container.graph()) == 0
    assert "✓ 2 stacks resolve" in caplog.text


def test_check_dependencies_names_the_stack_hiding_an_undeclared_dependency(
    container, filesystem, caplog
):
    _tree(filesystem, komga=TRAEFIK_LABEL, **{"reverse-proxy": "services: {}\n"})
    assert check_dependencies(container.graph()) == 1
    assert "    komga: reverse-proxy" in caplog.text


def test_check_dependencies_fails_on_an_unresolvable_graph_before_looking_for_gaps(
    container, filesystem, caplog
):
    _tree(filesystem, gamarr="x-homelab:\n    requires: [romm]\nservices: {}\n")
    assert check_dependencies(container.graph()) == 1
    assert "gamarr requires romm" in caplog.text


def test_check_dependencies_explains_the_shape_of_a_malformed_declaration(
    container, filesystem, caplog
):
    _tree(filesystem, paperless="x-homelab:\n    requires: reverse-proxy\nservices: {}\n")
    assert check_dependencies(container.graph()) == 1
    assert "x-homelab.requires must be a list" in caplog.text


def test_check_dependencies_reads_the_tree_once_however_many_questions_it_asks(
    container, filesystem
):
    _tree(filesystem, paperless=DECLARED, **{"reverse-proxy": "services: {}\n"})
    check_dependencies(container.graph())
    assert len(filesystem.reads) == 2
