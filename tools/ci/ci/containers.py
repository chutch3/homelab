"""The composition root.

Adapters are singletons — they hold no state worth rebuilding. Services are
factories because they close over configuration the CLI sets from its arguments.

``config`` carries everything read from outside the process: the repo root and
the merged environment. Tests build a Container and override a provider with a
fake, which is the whole reason the ports exist.
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
from ci.stackgraph import DependencyGraph, StackTree


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    filesystem = providers.Singleton(LocalFileSystem)
    commands = providers.Singleton(Subprocess)
    clock = providers.Singleton(SystemClock)
    console = providers.Singleton(StdoutConsole)

    catalog = providers.Factory(UnitCatalog, filesystem=filesystem, repo_root=config.repo_root)
    suites = providers.Factory(
        AppSuites,
        filesystem=filesystem,
        commands=commands,
        console=console,
        repo_root=config.repo_root,
    )
    suite_runner = providers.Factory(
        SuiteRunner,
        suites=suites,
        catalog=catalog,
        commands=commands,
        console=console,
        repo_root=config.repo_root,
    )
    registry_gc = providers.Factory(
        RegistryGc, catalog=catalog, commands=commands, clock=clock, console=console
    )
    idempotence = providers.Factory(IdempotenceCheck, commands=commands, console=console)

    stack_tree = providers.Factory(StackTree, filesystem=filesystem, repo_root=config.repo_root)
    graph = providers.Factory(DependencyGraph, tree=stack_tree, env=config.env)
    cluster = providers.Factory(SwarmCluster, commands=commands)
    deploy_plan = providers.Factory(
        DeployPlan, graph=graph, cluster=cluster, console=console
    )
