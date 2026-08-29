"""The composition root.

Adapters are singletons — they hold no state worth rebuilding, and so is
:class:`Docker`, whose whole contract is reading the cluster once per
invocation. Services are factories because they close over configuration the
CLI sets from its arguments.

``repo_root`` and ``env`` are everything read from outside the process, declared
as :class:`providers.Dependency` rather than a ``Configuration`` provider: they
are two typed values, not a config file, and a container told neither raises
instead of resolving to a default that would read the wrong tree.

Tests build a Container and override a provider with a fake, which is the whole
reason the ports exist.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from ci.adapters import CommandRunner, LocalFileSystem, SystemClock
from ci.affected import UnitCatalog
from ci.apptests import AppSuites, SuiteRunner
from ci.deploy import DeployPlanner
from ci.docker import Docker
from ci.gc import RegistryGc
from ci.idempotence import IdempotenceCheck
from ci.stackcheck import load_ratchet
from ci.stackgraph import DependencyGraph, StackTree


class Container(containers.DeclarativeContainer):
    repo_root = providers.Dependency(instance_of=str)
    env = providers.Dependency(instance_of=dict)

    filesystem = providers.Singleton(LocalFileSystem)
    commands = providers.Singleton(CommandRunner)
    clock = providers.Singleton(SystemClock)

    catalog = providers.Factory(UnitCatalog, filesystem=filesystem, repo_root=repo_root)
    suites = providers.Factory(
        AppSuites,
        filesystem=filesystem,
        commands=commands,
        repo_root=repo_root,
    )
    suite_runner = providers.Factory(
        SuiteRunner,
        suites=suites,
        catalog=catalog,
        commands=commands,
        repo_root=repo_root,
    )
    registry_gc = providers.Factory(RegistryGc, catalog=catalog, commands=commands, clock=clock)
    idempotence = providers.Factory(IdempotenceCheck, commands=commands)

    # Singleton, not Factory: StackTree promises each compose file is parsed
    # once, which a second instance would quietly break.
    stack_tree = providers.Singleton(StackTree, filesystem=filesystem, repo_root=repo_root)
    graph = providers.Factory(DependencyGraph, tree=stack_tree, env=env)
    ratchet = providers.Factory(load_ratchet, filesystem=filesystem, repo_root=repo_root)
    docker = providers.Singleton(Docker, commands=commands)
    planner = providers.Factory(DeployPlanner, graph=graph, docker=docker)
