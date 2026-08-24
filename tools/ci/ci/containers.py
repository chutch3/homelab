"""The composition root.

Adapters are singletons — they hold no state worth rebuilding, and so is
:class:`SwarmCluster`, whose whole contract is reading the cluster once per
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

from ci.adapters import LocalFileSystem, StdoutConsole, Subprocess, SystemClock
from ci.affected import UnitCatalog
from ci.apptests import AppSuites, SuiteRunner
from ci.cluster import SwarmCluster
from ci.deploy import DeployPlan
from ci.gc import RegistryGc
from ci.idempotence import IdempotenceCheck
from ci.stackgraph import DependencyCheck, DependencyGraph, StackTree


class Container(containers.DeclarativeContainer):
    repo_root = providers.Dependency(instance_of=str)
    env = providers.Dependency(instance_of=dict)

    filesystem = providers.Singleton(LocalFileSystem)
    commands = providers.Singleton(Subprocess)
    clock = providers.Singleton(SystemClock)
    console = providers.Singleton(StdoutConsole)

    catalog = providers.Factory(UnitCatalog, filesystem=filesystem, repo_root=repo_root)
    suites = providers.Factory(
        AppSuites,
        filesystem=filesystem,
        commands=commands,
        console=console,
        repo_root=repo_root,
    )
    suite_runner = providers.Factory(
        SuiteRunner,
        suites=suites,
        catalog=catalog,
        commands=commands,
        console=console,
        repo_root=repo_root,
    )
    registry_gc = providers.Factory(
        RegistryGc, catalog=catalog, commands=commands, clock=clock, console=console
    )
    idempotence = providers.Factory(IdempotenceCheck, commands=commands, console=console)

    stack_tree = providers.Factory(StackTree, filesystem=filesystem, repo_root=repo_root)
    graph = providers.Factory(DependencyGraph, tree=stack_tree, env=env)
    dependency_check = providers.Factory(DependencyCheck, graph=graph, console=console)
    cluster = providers.Singleton(SwarmCluster, commands=commands)
    deploy_plan = providers.Factory(
        DeployPlan, graph=graph, cluster=cluster, console=console
    )
