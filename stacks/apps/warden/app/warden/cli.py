from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx

from warden.container import Container
from warden.profiles.commands import diff_profiles, dump_profiles
from warden.profiles.presentation import CommandOutput, render_diff, render_error, render_summary
from warden.profiles.settings import parse_selection


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="warden", description="Run Warden or manage profile configuration.")
    groups = parser.add_subparsers(dest="group")
    groups.add_parser("serve", help="Start the HTTP server, hunter, and configured profile observer")
    profiles = groups.add_parser("profiles", help="Dump, validate, or compare profile configuration")
    commands = profiles.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate local portable profile configuration")
    validate.add_argument("--directory", type=Path, required=True)
    export = commands.add_parser("dump", help="Export current Arr profiles without changing the instance")
    export.add_argument("--source", choices=("radarr", "sonarr"), required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--profile", action="append", default=[])
    diff = commands.add_parser("diff", help="Compare local profiles with Arr without making changes")
    diff.add_argument("--source", choices=("radarr", "sonarr"), required=True)
    diff.add_argument("--directory", type=Path, required=True)
    diff.add_argument("--profile", action="append")
    diff.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    if args.group is None:
        parser.print_help()
        return 0
    container = Container()
    container.wire(modules=["warden.routes.health"])
    try:
        result = asyncio.run(dispatch(args, container))
    finally:
        container.unwire()
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.exit_code


async def dispatch(args: argparse.Namespace, container: Container) -> CommandOutput:
    """Resolve command dependencies lazily and shut down resources on every exit."""
    try:
        if args.group == "serve":
            await container.serve_command()
            return CommandOutput()
        try:
            store = container.profile_store()
            if args.command == "validate":
                return render_summary(args.command, store.load(args.directory))
            arr = container.arr_service()
            if inspect.isawaitable(arr):
                arr = await arr
            if args.command == "diff":
                raw = container.environment().get(f"WARDEN_{args.source.upper()}_PROFILES")
                selected = args.profile if args.profile is not None else parse_selection(raw)
                return render_diff(await diff_profiles(args.source, args.directory, selected, store, arr), args.json)
            return render_summary(args.command, await dump_profiles(args.source, args.output, args.profile, store, arr))
        except httpx.HTTPStatusError as exc:
            return render_error(f"Arr returned HTTP {exc.response.status_code}; {args.command} did not complete")
        except httpx.RequestError:
            return render_error(f"Arr request failed; {args.command} did not complete")
        except (ValueError, OSError) as exc:
            return render_error(str(exc))
    finally:
        shutdown = container.shutdown_resources()
        if inspect.isawaitable(shutdown):
            await shutdown
