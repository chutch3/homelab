from __future__ import annotations

import argparse
from collections.abc import Sequence

from warden.main import main as serve
from warden.profiles import cli as profiles


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="warden", description="Run Warden or manage profile catalogs.")
    commands = parser.add_subparsers(dest="group")
    commands.add_parser("serve", help="Start the HTTP server, hunter, and configured profile observer")
    profiles.configure_parser(commands.add_parser("profiles", help="Dump, validate, or compare profile catalogs"))
    args = parser.parse_args(argv)
    if args.group == "serve":
        serve()
        return 0
    if args.group == "profiles":
        return profiles.run(args)
    parser.print_help()
    return 0
