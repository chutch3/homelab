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


@pytest.fixture
def subject() -> Container:
    c = Container()
    c.repo_root.override(providers.Object(str(ROOT)))
    c.env.override(providers.Object({}))
    return c


class TestLifetimes:
    """Which providers are shared, and which are rebuilt."""

    def test_an_adapter_is_shared_because_it_holds_no_state_worth_rebuilding(self, subject):
        assert subject.filesystem() is subject.filesystem()

    def test_the_cluster_is_shared_so_one_invocation_reads_the_cluster_once(self, subject):
        assert subject.cluster() is subject.cluster()

    def test_a_service_is_rebuilt_so_it_closes_over_this_run_s_configuration(self, subject):
        assert subject.graph() is not subject.graph()


class TestRequiredConfiguration:
    """A container that was not told where it is, or what is switched on."""

    def test_a_container_without_a_repo_root_refuses_to_build_a_service(self):
        container = Container()
        container.env.override(providers.Object({}))
        with pytest.raises(errors.Error):
            container.graph()

    def test_a_container_without_an_environment_refuses_to_build_a_service(self):
        container = Container()
        container.repo_root.override(providers.Object(str(ROOT)))
        with pytest.raises(errors.Error):
            container.graph()

    def test_a_repo_root_that_is_not_a_path_is_rejected(self):
        container = Container()
        with pytest.raises(errors.Error):
            container.repo_root.override(providers.Object(object()))
            container.env.override(providers.Object({}))
            container.graph()

    def test_an_environment_that_is_not_a_mapping_is_rejected(self):
        container = Container()
        with pytest.raises(errors.Error):
            container.repo_root.override(providers.Object(str(ROOT)))
            container.env.override(providers.Object("PRIMARY_DNS_MANAGED=false"))
            container.graph()
