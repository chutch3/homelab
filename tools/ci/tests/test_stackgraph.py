"""Tests for the stack dependency graph (`ci deploy --plan` / `ci check-deps`).

The dangerous case is a false pass: an order that puts a stack before something
it needs, or a declaration the tree does not actually satisfy. Ordering and
cycle detection are exercised on plain mappings; everything that would read the
tree goes through a fake filesystem instead.
"""

from __future__ import annotations

import pytest
from dependency_injector import providers

from ci.adapters import Environment
from ci.stackgraph import DependencyGraph, Stack, StackTree, UnresolvedGraph, cycle_members, resolve
from conftest import ROOT, FakeFileSystem

ROUTED = {
    "reverse-proxy": [],
    "authentik": ["reverse-proxy"],
    "paperless": ["reverse-proxy", "authentik"],
}

TRAEFIK_LABEL = 'services:\n    a:\n        deploy:\n            labels: ["traefik.enable=true"]\n'
DECLARED = "x-homelab:\n    requires: [reverse-proxy]\n" + TRAEFIK_LABEL


def compose(**stacks: str) -> dict[str, str]:
    """Seed a fake tree: stack name -> compose text, all under stacks/apps/."""
    return {f"stacks/apps/{name}/docker-compose.yml": text for name, text in stacks.items()}


class TestResolve:
    """`resolve` — deploy order over a plain {stack: requires} mapping."""

    def test_orders_every_stack_after_its_dependencies(self):
        order = resolve(ROUTED)
        assert order.index("reverse-proxy") < order.index("authentik") < order.index("paperless")

    def test_orders_the_whole_tree_when_no_targets_are_named(self):
        assert set(resolve(ROUTED)) == set(ROUTED)

    def test_a_target_pulls_in_only_its_own_dependencies(self):
        assert resolve(ROUTED, targets=["authentik"]) == ["reverse-proxy", "authentik"]

    def test_independent_stacks_are_ordered_alphabetically(self):
        assert resolve({"beta": [], "alpha": [], "gamma": []}) == ["alpha", "beta", "gamma"]

    def test_the_same_graph_always_resolves_to_the_same_order(self):
        graph = {"d": ["a"], "c": ["a"], "b": ["c", "d"], "a": []}
        assert resolve(graph) == resolve(graph)

    def test_a_dependency_on_a_stack_that_does_not_exist_fails_naming_both_ends(self):
        with pytest.raises(UnresolvedGraph) as exc:
            resolve({"paperless": ["ghost-stack"]})
        assert "paperless requires ghost-stack" in str(exc.value)

    def test_a_target_that_does_not_exist_fails_naming_it(self):
        with pytest.raises(UnresolvedGraph, match="no such stack: ghost-stack"):
            resolve(ROUTED, targets=["ghost-stack"])

    def test_a_disabled_stack_is_dropped_from_the_order(self):
        assert resolve({"dns": [], "paperless": ["dns"]}, disabled=["dns"]) == ["paperless"]

    def test_a_disabled_stack_named_as_a_target_is_still_dropped(self):
        order = resolve(
            {"dns": [], "paperless": ["dns"]}, targets=["dns", "paperless"], disabled=["dns"]
        )
        assert order == ["paperless"]


class TestCycleMembers:
    """`cycle_members` — which stacks a cycle report should actually name."""

    def test_names_only_the_cycle_not_the_stacks_it_blocks(self):
        edges = {"authentik": ["paperless"], "paperless": ["authentik"], "komga": ["authentik"]}
        assert cycle_members(edges, sorted(edges)) == ["authentik", "paperless"]

    def test_a_cycle_report_names_its_members_and_nothing_else(self):
        graph = {"authentik": ["paperless"], "paperless": ["authentik"], "komga": ["authentik"]}
        with pytest.raises(UnresolvedGraph) as exc:
            resolve(graph)
        assert str(exc.value) == "dependency cycle among: authentik, paperless"

    def test_a_stack_that_requires_itself_is_a_cycle(self):
        with pytest.raises(UnresolvedGraph) as exc:
            resolve({"loop": ["loop"]})
        assert str(exc.value) == "dependency cycle among: loop"


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
        container.environment.override(
            providers.Object(Environment(filesystem, {"PRIMARY_DNS_MANAGED": value}))
        )
        subject = container.graph()
        assert subject.disabled() == {"dns"}
        assert subject.resolve() == ["paperless"]

    def test_a_gate_set_only_in_dotenv_is_honoured(self, container, filesystem):
        self._seed(filesystem, dns="services: {}\n")
        filesystem.files[".env"] = "# a comment\nPRIMARY_DNS_MANAGED=false\n"
        container.environment.override(
            providers.Object(Environment(filesystem, {}))
        )
        assert container.graph().disabled() == {"dns"}

    def test_the_process_environment_wins_over_dotenv(self, container, filesystem):
        self._seed(filesystem, dns="services: {}\n")
        filesystem.files[".env"] = "PRIMARY_DNS_MANAGED=false\n"
        container.environment.override(
            providers.Object(Environment(filesystem, {"PRIMARY_DNS_MANAGED": "true"}))
        )
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
