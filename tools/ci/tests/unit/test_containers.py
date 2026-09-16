"""The composition root's own contract: lifetimes, and refusing to run half-wired.

Lifetime is not cosmetic here. `SwarmCluster` caches the cluster read so a plan
over 54 stacks costs two docker calls; rebuilt per resolution it would cost two
per resolution. And a container missing its repo root or environment must say
so, rather than resolving to a default that silently reads the wrong tree.
"""

from __future__ import annotations

import pytest
from dependency_injector import errors, providers

from conftest import ROOT

from ci.containers import Container


class TestContainer:
    """`Container` — which providers are shared, and what it refuses to build."""

    @pytest.fixture
    def subject(self) -> Container:
        c = Container()
        c.repo_root.override(providers.Object(str(ROOT)))
        c.env.override(providers.Object({}))
        return c

    def test_filesystem_is_shared_because_it_holds_no_state_worth_rebuilding(self, subject):
        assert subject.filesystem() is subject.filesystem()

    def test_docker_is_shared_so_one_invocation_reads_the_cluster_once(self, subject):
        assert subject.docker() is subject.docker()

    def test_graph_is_rebuilt_so_it_closes_over_this_runs_configuration(self, subject):
        assert subject.graph() is not subject.graph()

    def test_repo_root_is_required_before_any_service_can_be_built(self):
        container = Container()
        container.env.override(providers.Object({}))
        with pytest.raises(errors.Error):
            container.graph()

    def test_env_is_required_before_any_service_can_be_built(self):
        container = Container()
        container.repo_root.override(providers.Object(str(ROOT)))
        with pytest.raises(errors.Error):
            container.graph()

    def test_repo_root_rejects_a_value_that_is_not_a_string(self):
        container = Container()
        with pytest.raises(errors.Error):
            container.repo_root.override(providers.Object(object()))
            container.env.override(providers.Object({}))
            container.graph()

    def test_env_rejects_a_value_that_is_not_a_mapping(self):
        container = Container()
        with pytest.raises(errors.Error):
            container.repo_root.override(providers.Object(str(ROOT)))
            container.env.override(providers.Object("PRIMARY_DNS_MANAGED=false"))
            container.graph()
