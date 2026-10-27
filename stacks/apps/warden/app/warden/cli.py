from __future__ import annotations

import argparse
import asyncio
import inspect
import sys
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path

import httpx
from dependency_injector.wiring import Provide, inject

from warden.arr_service import ArrService
from warden.container import Container
from warden.profiles.commands import diff_profiles, dump_profiles
from warden.profiles.files import ProfileStore
from warden.profiles.presentation import CommandOutput, render_diff, render_error, render_summary
from warden.profiles.settings import parse_selection


@inject
async def serve_command(
    args: argparse.Namespace,
    run: Callable[[], Awaitable[None]] = Provide[Container.serve_command.provider],
) -> CommandOutput:
    await run()
    return CommandOutput()


@inject
async def validate_command(
    args: argparse.Namespace,
    store: ProfileStore = Provide[Container.profile_store],
) -> CommandOutput:
    return render_summary("validate", store.load(args.directory))


@inject
async def dump_command(
    args: argparse.Namespace,
    store: ProfileStore = Provide[Container.profile_store],
    arr: ArrService = Provide[Container.arr_service],
) -> CommandOutput:
    documents = await dump_profiles(args.source, args.output, args.profile, store, arr)
    return render_summary("dump", documents)


@inject
async def diff_command(
    args: argparse.Namespace,
    store: ProfileStore = Provide[Container.profile_store],
    arr: ArrService = Provide[Container.arr_service],
    env: Mapping[str, str] = Provide[Container.environment],
) -> CommandOutput:
    selected = args.profile if args.profile is not None else parse_selection(env.get(f"WARDEN_{args.source.upper()}_PROFILES"))
    report = await diff_profiles(args.source, args.directory, selected, store, arr)
    return render_diff(report, args.json)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="warden", description="Run Warden or manage profile configuration.")
    groups = parser.add_subparsers(dest="group")
    serve = groups.add_parser("serve", help="Start the HTTP server, hunter, and configured profile observer")
    serve.set_defaults(func=serve_command, command="serve")
    profiles = groups.add_parser("profiles", help="Dump, validate, or compare profile configuration")
    commands = profiles.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate local portable profile configuration")
    validate.add_argument("--directory", type=Path, required=True)
    validate.set_defaults(func=validate_command)
    export = commands.add_parser("dump", help="Export current Arr profiles without changing the instance")
    export.add_argument("--source", choices=("radarr", "sonarr"), required=True)
    export.add_argument("--output", type=Path, required=True)
    export.add_argument("--profile", action="append", default=[])
    export.set_defaults(func=dump_command)
    diff = commands.add_parser("diff", help="Compare local profiles with Arr without making changes")
    diff.add_argument("--source", choices=("radarr", "sonarr"), required=True)
    diff.add_argument("--directory", type=Path, required=True)
    diff.add_argument("--profile", action="append")
    diff.add_argument("--json", action="store_true")
    diff.set_defaults(func=diff_command)
    return parser


async def dispatch(args: argparse.Namespace, container: Container) -> CommandOutput:
    """Run the selected handler with common error reporting and resource cleanup."""
    try:
        return await args.func(args)
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


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.group is None:
        parser.print_help()
        return 0
    container = Container()
    container.wire(modules=[__name__, "warden.routes.health"])
    try:
        result = asyncio.run(dispatch(args, container))
    finally:
        container.unwire()
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.exit_code
