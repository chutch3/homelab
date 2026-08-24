"""The ``ci`` command — one CLI surface for the repo's build/test tooling.

Subcommands:
  ci affected [REPO_ROOT] [FILE ...]   print the affected build matrix as JSON
                                       (files default to stdin, newline-separated)
  ci test [SELECTOR] [--tier T] [--affected]   run app pytest suites by tier
  ci images [REPO_ROOT]                 list every buildable image name (one per line)
  ci gc [--apply] [--cutoff-days N]     prune stale :sha/untagged ghcr versions (dry-run by default)
  ci idempotence PLAYBOOK [ANSIBLE ARGS] run a playbook twice; fail unless the second changes nothing
  ci deploy [STACK ...] --plan          print the resolved deploy order; deploy nothing
  ci check-deps [REPO_ROOT]             the x-homelab declarations resolve, and are complete

Handlers take their collaborators by injection, so tests drive them through the
container with fakes instead of touching the filesystem or spawning processes.
"""

from __future__ import annotations

import argparse
import json
import sys

from dependency_injector.wiring import Provide, inject

from ci.adapters import CommandRunner, Console
from ci.affected import UnitCatalog
from ci.apptests import TestSuites, select_projects, tiers_to_run
from ci.containers import Container
from ci.gc import RegistryGc
from ci.idempotence import IdempotenceCheck
from ci.stackgraph import DependencyGraph, UnresolvedGraph


@inject
def _cmd_affected(
    args: argparse.Namespace,
    catalog: UnitCatalog = Provide[Container.catalog],
    console: Console = Provide[Container.console],
) -> int:
    changed = args.files or [line.strip() for line in sys.stdin if line.strip()]
    console.out(json.dumps(catalog.matrix(changed)))
    return 0


@inject
def _cmd_test(
    args: argparse.Namespace,
    suites: TestSuites = Provide[Container.suites],
    catalog: UnitCatalog = Provide[Container.catalog],
    commands: CommandRunner = Provide[Container.commands],
    console: Console = Provide[Container.console],
) -> int:
    if args.affected:
        # Test only the projects under the contexts a change vs the base touched.
        diff = commands.run(
            ["git", "-C", args.repo_root, "diff", "--name-only", f"{args.base}...HEAD"],
            capture=True, check=True,
        ).stdout.split()
        contexts = {entry["context"] for entry in catalog.matrix(diff)}
        pick = lambda ps: sorted({p for c in contexts for p in select_projects(ps, c)})  # noqa: E731
    else:
        pick = lambda ps: select_projects(ps, args.selector)  # noqa: E731

    # No --tier → the gated default suite (unit+integration, combined coverage).
    py_rc, py_ran = suites.run_python(
        pick(suites.python_projects()), tiers_to_run(args.tier), gated=args.tier is None
    )
    js_rc, js_ran = suites.run_js(pick(suites.js_projects()), args.tier)
    if not (py_ran or js_ran):
        console.out("No matching test suites.")
    return py_rc or js_rc


@inject
def _cmd_images(
    args: argparse.Namespace,
    catalog: UnitCatalog = Provide[Container.catalog],
    console: Console = Provide[Container.console],
) -> int:
    for image in catalog.image_names():
        console.out(image)
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
    graph: DependencyGraph = Provide[Container.graph],
    console: Console = Provide[Container.console],
) -> int:
    try:
        order = graph.resolve(args.stacks or None)
    except UnresolvedGraph as exc:
        console.err(f"✗ {exc}")
        return 1
    for stack in order:
        console.out(stack)
    console.err(f"\n{len(order)} stack(s) — plan only, nothing deployed.")
    return 0


@inject
def _cmd_check_deps(
    args: argparse.Namespace,
    graph: DependencyGraph = Provide[Container.graph],
    console: Console = Provide[Container.console],
) -> int:
    try:
        stacks = graph.stacks()
        graph.resolve()
    except UnresolvedGraph as exc:
        console.out(f"✗ {exc}")
        return 1
    if missing := graph.undeclared():
        console.out("✗ dependencies visible in the compose file but not declared in x-homelab.requires:")
        for stack, requires in sorted(missing.items()):
            console.out(f"    {stack}: {', '.join(sorted(requires))}")
        return 1
    console.out(f"✓ {len(stacks)} stacks resolve, with every dependency they reveal declared")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ci")
    sub = parser.add_subparsers(dest="cmd", required=True)

    aff = sub.add_parser("affected", help="print the affected build matrix as JSON")
    aff.add_argument("repo_root", nargs="?", default=".")
    aff.add_argument("files", nargs="*")
    aff.set_defaults(func=_cmd_affected)

    test = sub.add_parser("test", help="run app pytest suites by tier")
    test.add_argument("selector", nargs="?", default=None, help="app name or repo-relative path")
    test.add_argument("--tier", default=None, choices=["unit", "integration", "e2e"])
    test.add_argument("--affected", action="store_true", help="only projects changed vs --base")
    test.add_argument("--base", default="origin/main")
    test.add_argument("--repo-root", default=".")
    test.set_defaults(func=_cmd_test)

    images = sub.add_parser("images", help="list every buildable image name (one per line)")
    images.add_argument("repo_root", nargs="?", default=".")
    images.set_defaults(func=_cmd_images)

    gc_p = sub.add_parser("gc", help="prune stale :sha/untagged ghcr versions (dry-run by default)")
    gc_p.add_argument("repo_root", nargs="?", default=".")
    gc_p.add_argument("--cutoff-days", type=int, default=14)
    gc_p.add_argument("--apply", action="store_true", help="actually delete (default: dry-run)")
    gc_p.set_defaults(func=_cmd_gc)

    idem = sub.add_parser("idempotence", help="run a playbook twice; the second must change nothing")
    idem.add_argument("playbook")
    # REMAINDER so ansible's own flags (-i, --limit, --skip-tags) pass through unparsed.
    idem.add_argument("ansible_args", nargs=argparse.REMAINDER,
                      help="passed through to ansible-playbook")
    idem.set_defaults(func=_cmd_idempotence)

    dep = sub.add_parser("deploy", help="print the resolved deploy order (--plan is the only mode)")
    dep.add_argument("stacks", nargs="*", help="deploy targets; omit for every stack")
    # Required until 1.3 gives `ci deploy` something to execute — refusing here
    # beats a flag that silently means nothing.
    dep.add_argument("--plan", action="store_true", required=True,
                     help="print the order and deploy nothing")
    dep.add_argument("--repo-root", default=".")
    dep.set_defaults(func=_cmd_deploy)

    deps = sub.add_parser("check-deps", help="the x-homelab declarations resolve, and are complete")
    deps.add_argument("repo_root", nargs="?", default=".")
    deps.set_defaults(func=_cmd_check_deps)
    return parser


def build_container(args: argparse.Namespace) -> Container:
    """Wire the container for one invocation, with this run's repo root."""
    container = Container()
    container.config.repo_root.from_value(getattr(args, "repo_root", ".") or ".")
    container.wire(modules=[__name__])
    return container


def main() -> None:
    args = build_parser().parse_args()
    build_container(args)
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
