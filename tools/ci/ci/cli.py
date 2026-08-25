"""The ``ci`` command — one CLI surface for the repo's build/test tooling.

Subcommands:
  ci affected [FILE ...]                print the affected build matrix as JSON
                                        (files default to stdin, newline-separated)
  ci projects [FILE ...]                print the test projects a change affects, as JSON
  ci test [SELECTOR] [--tier T] [--affected]   run app pytest suites by tier
  ci images                             list every buildable image name (one per line)
  ci gc [--apply] [--cutoff-days N]     prune stale :sha/untagged ghcr versions (dry-run by default)
  ci idempotence PLAYBOOK [ANSIBLE ARGS] run a playbook twice; fail unless the second changes nothing
  ci deploy [STACK ...] --plan          print the deploy plan and live state; deploy nothing
  ci check-deps                         the x-homelab declarations resolve, and are complete

Every subcommand takes ``--repo-root`` (default ``.``); nothing takes it
positionally, so a positional argument always means the same thing.

Each handler is one call into an injected service — behaviour lives in the
services, not here — so tests drive them through the container with fakes
instead of touching the filesystem or spawning processes.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys

from dependency_injector import providers
from dependency_injector.wiring import Provide, inject

from ci.affected import UnitCatalog
from ci.apptests import AppSuites, SuiteRunner
from ci.config import load_env
from ci.containers import Container
from ci.deploy import DeployPlanner
from ci.gc import RegistryGc
from ci.idempotence import IdempotenceCheck
from ci.stackgraph import DependencyGraph, check_dependencies


@inject
def _cmd_affected(
    args: argparse.Namespace,
    catalog: UnitCatalog = Provide[Container.catalog],
) -> int:
    changed = args.files or [line.strip() for line in sys.stdin if line.strip()]
    print(json.dumps(catalog.matrix(changed)))
    return 0


@inject
def _cmd_test(
    args: argparse.Namespace,
    suite_runner: SuiteRunner = Provide[Container.suite_runner],
) -> int:
    return suite_runner.run(args.selector, args.tier, args.affected, args.base)


@inject
def _cmd_projects(
    args: argparse.Namespace,
    suites: AppSuites = Provide[Container.suites],
    suite_runner: SuiteRunner = Provide[Container.suite_runner],
) -> int:
    changed = args.files or [line.strip() for line in sys.stdin if line.strip()]
    affected = set(suite_runner.affected_projects(suites.python_projects(), changed))
    affected |= set(suite_runner.affected_projects(suites.js_projects(), changed))
    print(json.dumps([{"project": p} for p in sorted(affected)]))
    return 0


@inject
def _cmd_images(
    args: argparse.Namespace,
    catalog: UnitCatalog = Provide[Container.catalog],
) -> int:
    for image in catalog.image_names():
        print(image)
    return 0


@inject
def _cmd_gc(
    args: argparse.Namespace,
    registry_gc: RegistryGc = Provide[Container.registry_gc],
) -> int:
    registry_gc.prune(cutoff_days=args.cutoff_days, apply=args.apply)
    return 0


@inject
def _cmd_idempotence(
    args: argparse.Namespace,
    idempotence: IdempotenceCheck = Provide[Container.idempotence],
) -> int:
    return idempotence.verify(args.playbook, args.ansible_args)


@inject
def _cmd_deploy(
    args: argparse.Namespace,
    planner: DeployPlanner = Provide[Container.planner],
) -> int:
    return planner.report(args.stacks or None)


@inject
def _cmd_check_deps(
    args: argparse.Namespace,
    graph: DependencyGraph = Provide[Container.graph],
) -> int:
    return check_dependencies(graph)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci")
    sub = parser.add_subparsers(dest="cmd", required=True)

    aff = sub.add_parser("affected", help="print the affected build matrix as JSON")
    aff.add_argument("files", nargs="*")
    aff.add_argument("--repo-root", default=".")
    aff.set_defaults(func=_cmd_affected)

    test = sub.add_parser("test", help="run app pytest suites by tier")
    test.add_argument("selector", nargs="?", default=None, help="app name or repo-relative path")
    test.add_argument("--tier", default=None, choices=["unit", "integration", "e2e"])
    test.add_argument("--affected", action="store_true", help="only projects changed vs --base")
    test.add_argument("--base", default="origin/main")
    test.add_argument("--repo-root", default=".")
    test.set_defaults(func=_cmd_test)

    proj = sub.add_parser("projects", help="print the test projects a change affects, as JSON")
    proj.add_argument("files", nargs="*")
    proj.add_argument("--repo-root", default=".")
    proj.set_defaults(func=_cmd_projects)

    images = sub.add_parser("images", help="list every buildable image name (one per line)")
    images.add_argument("--repo-root", default=".")
    images.set_defaults(func=_cmd_images)

    gc_p = sub.add_parser("gc", help="prune stale :sha/untagged ghcr versions (dry-run by default)")
    gc_p.add_argument("--cutoff-days", type=int, default=14)
    gc_p.add_argument("--apply", action="store_true", help="actually delete (default: dry-run)")
    gc_p.add_argument("--repo-root", default=".")
    gc_p.set_defaults(func=_cmd_gc)

    idem = sub.add_parser("idempotence", help="run a playbook twice; the second must change nothing")
    idem.add_argument("playbook")
    # REMAINDER so ansible's own flags (-i, --limit, --skip-tags) pass through unparsed.
    idem.add_argument("ansible_args", nargs=argparse.REMAINDER,
                      help="passed through to ansible-playbook")
    # Unused by the check itself, but the composition root reads it off every
    # subcommand's args. REMAINDER swallows everything after the playbook, so
    # this one only takes effect before it: `ci idempotence --repo-root X play.yml`.
    idem.add_argument("--repo-root", default=".")
    idem.set_defaults(func=_cmd_idempotence)

    dep = sub.add_parser("deploy", help="print the deploy plan and live state (--plan is the only mode)")
    dep.add_argument("stacks", nargs="*", help="deploy targets; omit for every stack")
    # Required until 1.3 gives `ci deploy` something to execute — refusing here
    # beats a flag that silently means nothing.
    dep.add_argument("--plan", action="store_true", required=True,
                     help="print the plan and deploy nothing")
    dep.add_argument("--repo-root", default=".")
    dep.set_defaults(func=_cmd_deploy)

    deps = sub.add_parser("check-deps", help="the x-homelab declarations resolve, and are complete")
    deps.add_argument("--repo-root", default=".")
    deps.set_defaults(func=_cmd_check_deps)
    return parser


def build_container(args: argparse.Namespace, process_env: dict[str, str] | None = None) -> Container:
    """Wire the container for one invocation: this run's repo root and environment."""
    container = Container()
    container.repo_root.override(providers.Object(args.repo_root))
    container.env.override(
        providers.Object(
            load_env(
                container.filesystem(),
                args.repo_root,
                dict(os.environ if process_env is None else process_env),
            )
        )
    )
    container.wire(modules=[__name__])
    return container


def main() -> None:
    # Diagnostics go to stderr through logging; stdout carries only the payload,
    # which callers pipe and parse.
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    args = build_parser().parse_args()
    build_container(args)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
