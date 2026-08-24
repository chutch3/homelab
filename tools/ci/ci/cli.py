"""The ``ci`` command — one CLI surface for the repo's build/test tooling.

Subcommands:
  ci affected [REPO_ROOT] [FILE ...]   print the affected build matrix as JSON
                                       (files default to stdin, newline-separated)
  ci test [SELECTOR] [--tier T] [--affected]   run app pytest suites by tier
  ci images [REPO_ROOT]                 list every buildable image name (one per line)
  ci gc [--apply] [--cutoff-days N]     prune stale :sha/untagged ghcr versions (dry-run by default)
  ci idempotence PLAYBOOK [ANSIBLE ARGS] run a playbook twice; fail unless the second changes nothing
  ci deploy [STACK ...] --plan          print the resolved deploy order; deploy nothing
  ci check-deps [COMPOSE ...]           the x-homelab dependency declarations resolve, and are complete
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from ci import affected, apptests, gc, idempotence, stackgraph


def _cmd_affected(args: argparse.Namespace) -> int:
    changed = args.files or [line.strip() for line in sys.stdin if line.strip()]
    print(json.dumps(affected.compute_matrix(args.repo_root, changed)))
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    if args.affected:
        # Test only the projects under the contexts a change vs the base touched.
        diff = subprocess.run(
            ["git", "-C", args.repo_root, "diff", "--name-only", f"{args.base}...HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.split()
        contexts = {entry["context"] for entry in affected.compute_matrix(args.repo_root, diff)}
        pick = lambda ps: sorted({p for c in contexts for p in apptests.select_projects(ps, c)})  # noqa: E731
    else:
        pick = lambda ps: apptests.select_projects(ps, args.selector)  # noqa: E731

    # No --tier → the gated default suite (unit+integration, combined coverage).
    py_rc, py_ran = apptests.run_tests(
        args.repo_root, pick(apptests.discover_test_projects(args.repo_root)),
        apptests.tiers_to_run(args.tier), gated=args.tier is None,
    )
    js_rc, js_ran = apptests.run_js_tests(
        args.repo_root, pick(apptests.discover_js_projects(args.repo_root)), args.tier,
    )
    if not (py_ran or js_ran):
        print("No matching test suites.")
    return py_rc or js_rc


def _cmd_images(args: argparse.Namespace) -> int:
    for image in affected.list_images(args.repo_root):
        print(image)
    return 0


def _cmd_gc(args: argparse.Namespace) -> int:
    gc.prune(args.repo_root, cutoff_days=args.cutoff_days, apply=args.apply)
    return 0


def _cmd_idempotence(args: argparse.Namespace) -> int:
    return idempotence.verify(args.playbook, args.ansible_args)


def _cmd_deploy(args: argparse.Namespace) -> int:
    graph = stackgraph.load_graph(args.repo_root)
    disabled = stackgraph.disabled_by_capability()
    try:
        order = stackgraph.resolve(graph, args.stacks or None, sorted(disabled))
    except stackgraph.UnresolvedGraph as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1
    for stack in order:
        print(stack)
    print(f"\n{len(order)} stack(s) — plan only, nothing deployed.", file=sys.stderr)
    return 0


def _cmd_check_deps(args: argparse.Namespace) -> int:
    graph = stackgraph.load_graph(args.repo_root)
    try:
        stackgraph.resolve(graph)
    except stackgraph.UnresolvedGraph as exc:
        print(f"✗ {exc}")
        return 1
    if missing := stackgraph.undeclared(args.repo_root, args.compose or None):
        print("✗ dependencies visible in the compose file but not declared in x-homelab.requires:")
        for stack, requires in sorted(missing.items()):
            print(f"    {stack}: {', '.join(sorted(requires))}")
        return 1
    print(f"✓ {len(graph)} stacks resolve; every dependency visible in the checked files is declared")
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
    deps.add_argument("compose", nargs="*", help="compose files to check; omit for every stack")
    deps.add_argument("--repo-root", default=".")
    deps.set_defaults(func=_cmd_check_deps)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
