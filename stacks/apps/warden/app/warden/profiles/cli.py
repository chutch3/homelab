from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import httpx

from warden.clients.arr import RadarrClient, SonarrClient
from warden.profiles.files import LocalCatalogStore
from warden.profiles.commands import diff_profiles, dump_profiles
from warden.profiles.settings import parse_selection
from warden.profiles.presentation import CommandOutput, render_diff, render_error, render_summary


class HttpArrProfileReader:
    """HTTP adapter; configuration is supplied by the CLI composition boundary."""

    def __init__(self, source: Literal["radarr", "sonarr"], url: str, api_key: str) -> None:
        self.source = source
        self.url = url
        self.api_key = api_key

    async def read(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        if not self.url or not self.api_key:
            prefix = f"WARDEN_{self.source.upper()}"
            raise ValueError(f"{prefix}_URL and {prefix}_API_KEY are required")
        async with httpx.AsyncClient(timeout=30.0) as http:
            cls = RadarrClient if self.source == "radarr" else SonarrClient
            client = cls(name=self.source, base_url=self.url, http=http, api_key=self.api_key)
            return await client.list_quality_profiles(), await client.list_custom_formats()


def configure_parser(parser: argparse.ArgumentParser) -> None:
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Validate a local portable profile catalog")
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


def execute(args: argparse.Namespace) -> CommandOutput:
    store = LocalCatalogStore()
    try:
        if args.command == "validate":
            return render_summary(args.command, store.load(args.directory))
        prefix = f"WARDEN_{args.source.upper()}"
        reader = HttpArrProfileReader(args.source, os.getenv(f"{prefix}_URL", ""), os.getenv(f"{prefix}_API_KEY", ""))
        if args.command == "diff":
            selected = args.profile if args.profile is not None else parse_selection(os.getenv(f"{prefix}_PROFILES"))
            report = asyncio.run(diff_profiles(args.source, args.directory, selected, store, reader))
            return render_diff(report, args.json)
        documents = asyncio.run(dump_profiles(args.source, args.output, args.profile, store, reader))
        return render_summary(args.command, documents)
    except httpx.HTTPStatusError as exc:
        return render_error(f"Arr returned HTTP {exc.response.status_code}; {args.command} did not complete")
    except httpx.RequestError:
        return render_error(f"Arr request failed; {args.command} did not complete")
    except (ValueError, OSError) as exc:
        return render_error(str(exc))


def run(args: argparse.Namespace) -> int:
    result = execute(args)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.exit_code


def main(argv: Sequence[str] | None = None) -> int:
    """Compatibility entry point for the original profile-only module command."""
    parser = argparse.ArgumentParser(prog="warden-profiles")
    configure_parser(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
