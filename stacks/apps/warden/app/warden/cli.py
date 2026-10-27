from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence
from pathlib import Path

import httpx

from warden.arr_service import ArrService
from warden.clients.arr import RadarrClient, SonarrClient
from warden.profiles.codec import profile_codec
from warden.profiles.commands import diff_profiles, dump_profiles
from warden.profiles.files import LocalProfileFiles, ProfileStore
from warden.profiles.presentation import CommandOutput, render_diff, render_error, render_summary
from warden.profiles.settings import parse_selection
from warden.serve import serve


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
    result = asyncio.run(dispatch(args))
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.exit_code


async def dispatch(args: argparse.Namespace) -> CommandOutput:
    """Own command dependencies and their lifetime; domain operations receive them."""
    if args.group == "serve":
        await serve()
        return CommandOutput()
    store = ProfileStore(LocalProfileFiles(), profile_codec())
    try:
        if args.command == "validate":
            return render_summary(args.command, store.load(args.directory))
        prefix = f"WARDEN_{args.source.upper()}"
        url, api_key = os.getenv(f"{prefix}_URL", ""), os.getenv(f"{prefix}_API_KEY", "")
        async with httpx.AsyncClient(timeout=30.0) as http:
            client_type = RadarrClient if args.source == "radarr" else SonarrClient
            clients = {args.source: client_type(name=args.source, base_url=url, http=http, api_key=api_key)} if url and api_key else {}
            arr = ArrService(clients)
            if args.command == "diff":
                selected = args.profile if args.profile is not None else parse_selection(os.getenv(f"{prefix}_PROFILES"))
                return render_diff(await diff_profiles(args.source, args.directory, selected, store, arr), args.json)
            return render_summary(args.command, await dump_profiles(args.source, args.output, args.profile, store, arr))
    except httpx.HTTPStatusError as exc:
        return render_error(f"Arr returned HTTP {exc.response.status_code}; {args.command} did not complete")
    except httpx.RequestError:
        return render_error(f"Arr request failed; {args.command} did not complete")
    except (ValueError, OSError) as exc:
        return render_error(str(exc))
