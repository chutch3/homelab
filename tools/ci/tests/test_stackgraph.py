"""Tests for the stack dependency graph (the `ci deploy --plan` / `ci check-deps` logic).

Ordering, cycle and unknown-dependency detection are pure functions over a
{stack: requires} mapping; reading the tree is glue. The dangerous case is a
false pass — an order that puts a stack before something it needs, or a
declaration the tree does not actually satisfy.
"""

from __future__ import annotations

import pytest

from ci.stackgraph import (
    UnresolvedGraph,
    disabled_by_capability,
    inferred_requires,
    resolve,
    undeclared,
)

ROUTED = {"reverse-proxy": [], "authentik": ["reverse-proxy"], "paperless": ["reverse-proxy", "authentik"]}


class TestResolve:
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

    def test_a_cycle_fails_naming_its_members(self):
        with pytest.raises(UnresolvedGraph) as exc:
            resolve({"a": ["b"], "b": ["a"]})
        assert "a" in str(exc.value) and "b" in str(exc.value)

    def test_a_dependency_on_a_stack_that_does_not_exist_fails_naming_it(self):
        with pytest.raises(UnresolvedGraph) as exc:
            resolve({"paperless": ["ghost"]})
        assert "ghost" in str(exc.value)
        assert "paperless" in str(exc.value)

    def test_a_target_that_does_not_exist_fails_naming_it(self):
        with pytest.raises(UnresolvedGraph) as exc:
            resolve(ROUTED, targets=["ghost"])
        assert "ghost" in str(exc.value)

    def test_a_disabled_stack_is_dropped_from_the_order(self):
        assert "dns" not in resolve({"dns": [], "paperless": ["dns"]}, disabled=["dns"])

    def test_an_edge_to_a_disabled_stack_is_dropped_rather_than_failing(self):
        assert resolve({"dns": [], "paperless": ["dns"]}, disabled=["dns"]) == ["paperless"]

    def test_a_disabled_stack_named_as_a_target_is_still_dropped(self):
        assert resolve({"dns": [], "paperless": ["dns"]}, targets=["dns", "paperless"], disabled=["dns"]) == [
            "paperless"
        ]


class TestInferredRequires:
    def test_a_traefik_router_implies_the_reverse_proxy(self):
        assert "reverse-proxy" in inferred_requires("paperless", '- "traefik.enable=true"')

    def test_no_traefik_router_implies_nothing(self):
        assert inferred_requires("kopia", "image: kopia/kopia") == set()

    def test_a_forward_auth_middleware_implies_authentik(self):
        compose = '- "traefik.http.routers.tor.middlewares=authentik@swarm"'
        assert "authentik" in inferred_requires("tor-browser", compose)

    def test_an_oidc_issuer_on_the_auth_host_implies_authentik(self):
        assert "authentik" in inferred_requires("mealie", "- OIDC_CONFIGURATION_URL=https://auth.${BASE_DOMAIN}/x")

    def test_a_stack_never_requires_itself(self):
        compose = '- "traefik.enable=true"\n- AUTHENTIK_HOST=https://auth.${BASE_DOMAIN}'
        assert "authentik" not in inferred_requires("authentik", compose)

    def test_the_reverse_proxy_does_not_require_itself(self):
        assert inferred_requires("reverse-proxy", '- "traefik.enable=true"') == set()


def _tree(root, stacks):
    for name, body in stacks.items():
        stack = root / "stacks" / "apps" / name
        stack.mkdir(parents=True)
        (stack / "docker-compose.yml").write_text(body)
    return root


class TestUndeclared:
    ROUTED_UNDECLARED = 'services:\n    a:\n        deploy:\n            labels: ["traefik.enable=true"]\n'
    ROUTED_DECLARED = "x-homelab:\n    requires: [reverse-proxy]\n" + ROUTED_UNDECLARED

    def test_names_the_dependency_the_compose_reveals_but_does_not_declare(self, tmp_path):
        _tree(tmp_path, {"paperless": self.ROUTED_UNDECLARED})
        assert undeclared(tmp_path) == {"paperless": {"reverse-proxy"}}

    def test_a_declared_dependency_is_not_a_violation(self, tmp_path):
        _tree(tmp_path, {"paperless": self.ROUTED_DECLARED})
        assert undeclared(tmp_path) == {}

    def test_a_declaration_the_compose_cannot_reveal_is_not_a_violation(self, tmp_path):
        _tree(tmp_path, {"beholder": "x-homelab:\n    requires: [postal]\nservices:\n    a:\n        image: x\n"})
        assert undeclared(tmp_path) == {}

    def test_scoping_to_files_ignores_violations_elsewhere(self, tmp_path):
        _tree(tmp_path, {"kopia": self.ROUTED_UNDECLARED, "mealie": self.ROUTED_UNDECLARED})
        scoped = [str(tmp_path / "stacks/apps/mealie/docker-compose.yml")]
        assert set(undeclared(tmp_path, paths=scoped)) == {"mealie"}


class TestDisabledByCapability:
    def test_an_unset_gate_leaves_its_provider_enabled(self):
        assert disabled_by_capability({}) == set()

    @pytest.mark.parametrize("value", ["false", "FALSE", "no", "0", ""])
    def test_a_falsey_gate_disables_its_provider(self, value):
        assert disabled_by_capability({"PRIMARY_DNS_MANAGED": value}) == {"dns"}

    def test_a_truthy_gate_leaves_its_provider_enabled(self):
        assert disabled_by_capability({"PRIMARY_DNS_MANAGED": "true"}) == set()


class TestCycleReporting:
    def test_names_only_the_cycle_not_the_stacks_it_blocks(self):
        graph = {"a": ["b"], "b": ["a"], "blocked": ["a"], "also-blocked": ["blocked"]}
        with pytest.raises(UnresolvedGraph) as exc:
            resolve(graph)
        message = str(exc.value)
        assert "a" in message and "b" in message
        assert "blocked" not in message

    def test_a_stack_that_requires_itself_is_a_cycle(self):
        with pytest.raises(UnresolvedGraph, match="loop"):
            resolve({"loop": ["loop"]})
