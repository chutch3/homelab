"""The composition root.

Adapters are singletons — they hold no state worth rebuilding. Services are
factories because they close over ``config.repo_root``, which the CLI sets from
its arguments after the container is built.

Tests build a Container and override a provider (usually ``filesystem`` or
``commands``) with a fake, which is the whole reason the seams exist.
"""

from __future__ import annotations

from dependency_injector import containers, providers

from ci.adapters import Clock, CommandRunner, Console, Environment, FileSystem
from ci.affected import UnitCatalog
from ci.apptests import TestSuites
from ci.gc import RegistryGc
from ci.idempotence import IdempotenceCheck
from ci.stackgraph import DependencyGraph, StackTree


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    filesystem = providers.Singleton(FileSystem)
    commands = providers.Singleton(CommandRunner)
    clock = providers.Singleton(Clock)
    console = providers.Singleton(Console)
    environment = providers.Singleton(Environment, filesystem=filesystem)

    catalog = providers.Factory(
        UnitCatalog, filesystem=filesystem, repo_root=config.repo_root
    )
    suites = providers.Factory(
        TestSuites,
        filesystem=filesystem,
        commands=commands,
        console=console,
        repo_root=config.repo_root,
    )
    registry_gc = providers.Factory(
        RegistryGc, catalog=catalog, commands=commands, clock=clock, console=console
    )
    idempotence = providers.Factory(IdempotenceCheck, commands=commands, console=console)

    stack_tree = providers.Factory(
        StackTree, filesystem=filesystem, repo_root=config.repo_root
    )
    graph = providers.Factory(
        DependencyGraph,
        tree=stack_tree,
        environment=environment,
        repo_root=config.repo_root,
    )
