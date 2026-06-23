"""The ``ci`` command — one CLI surface for the repo's build/test tooling.

Subcommands:
  ci affected [REPO_ROOT] [FILE ...]   print the affected build matrix as JSON
                                       (files default to stdin, newline-separated)
  ci test [SELECTOR] [--tier T] [--affected]   run app pytest suites by tier
  ci gc [--apply] [--cutoff-days N]    prune stale :sha/untagged ghcr versions (dry-run by default)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

from ci import affected, apptests, gc


def _cmd_affected(args: argparse.Namespace) -> int:
    changed = args.files or [line.strip() for line in sys.stdin if line.strip()]
    print(json.dumps(affected.compute_matrix(args.repo_root, changed)))
    return 0


def _cmd_test(args: argparse.Namespace) -> int:
    projects = apptests.discover_test_projects(args.repo_root)
    if args.affected:
        # Test only the projects under the contexts a change vs the base touched.
        diff = subprocess.run(
            ["git", "-C", args.repo_root, "diff", "--name-only", f"{args.base}...HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.split()
        contexts = {entry["context"] for entry in affected.compute_matrix(args.repo_root, diff)}
        selected = sorted({p for c in contexts for p in apptests.select_projects(projects, c)})
    else:
        selected = apptests.select_projects(projects, args.selector)
    return apptests.run_tests(args.repo_root, selected, apptests.tiers_to_run(args.tier))


def _cmd_gc(args: argparse.Namespace) -> int:
    gc.prune(args.repo_root, cutoff_days=args.cutoff_days, apply=args.apply)
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
    test.add_argument("--tier", default="all", choices=["unit", "integration", "e2e", "all"])
    test.add_argument("--affected", action="store_true", help="only projects changed vs --base")
    test.add_argument("--base", default="origin/main")
    test.add_argument("--repo-root", default=".")
    test.set_defaults(func=_cmd_test)

    gc_p = sub.add_parser("gc", help="prune stale :sha/untagged ghcr versions (dry-run by default)")
    gc_p.add_argument("repo_root", nargs="?", default=".")
    gc_p.add_argument("--cutoff-days", type=int, default=14)
    gc_p.add_argument("--apply", action="store_true", help="actually delete (default: dry-run)")
    gc_p.set_defaults(func=_cmd_gc)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
