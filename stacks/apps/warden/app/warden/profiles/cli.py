from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import httpx

from warden.clients.arr import RadarrClient, SonarrClient
from warden.profiles.catalog import Document
from warden.profiles.files import load_catalog, write_catalog
from warden.profiles.export import export_documents
from warden.profiles.compare import compare_catalog, select_profiles
from warden.profiles.settings import parse_selection


async def read_arr(source: Literal["radarr", "sonarr"], url: str, api_key: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    async with httpx.AsyncClient(timeout=30.0) as http:
        cls = RadarrClient if source == "radarr" else SonarrClient
        client = cls(name=source, base_url=url, http=http, api_key=api_key)
        profiles = await client.list_quality_profiles()
        formats = await client.list_custom_formats()
    return profiles, formats


async def dump(source: Literal["radarr", "sonarr"], url: str, api_key: str, selected: Sequence[str]) -> tuple[Document, ...]:
    profiles, formats = await read_arr(source, url, api_key)
    try:
        return export_documents(source, profiles, formats, selected)
    except (KeyError, TypeError) as exc:
        raise ValueError("Arr response has an unsupported or incomplete profile structure") from exc


def _print_diff(report: dict[str, Any], as_json: bool) -> int:
    changes, conflicts = report["changes"], report["conflicts"]
    if as_json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif not report["profiles"]:
        print(f"{report['source']}: profile comparison disabled.")
    elif not changes:
        count = len(report["profiles"])
        print(f"{report['source']}: no differences ({count} profile{'s' if count != 1 else ''}).")
    else:
        resources = len({(change["kind"], change["name"]) for change in changes})
        print(f"{report['source']}: {len(changes)} change{'s' if len(changes) != 1 else ''} "
              f"across {resources} resource{'s' if resources != 1 else ''}.")
        for change in changes:
            current = json.dumps(change["current"], ensure_ascii=False, sort_keys=True)
            desired = json.dumps(change["desired"], ensure_ascii=False, sort_keys=True)
            print(f"  {change['kind']} {json.dumps(change['name'])}: {change['field']}: {current} -> {desired}")
        for conflict in conflicts:
            print(f"  conflict: custom_format {json.dumps(conflict['name'])} also used by unselected profiles: "
                  + ", ".join(json.dumps(name) for name in conflict["profiles"]))
    return 1 if conflicts else (2 if changes else 0)


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


def run(args: argparse.Namespace) -> int:
    try:
        if args.command == "diff":
            documents = load_catalog(args.directory)
            requested = args.profile
            if requested is None:
                requested = parse_selection(os.getenv(f"WARDEN_{args.source.upper()}_PROFILES"))
            selected = select_profiles(args.source, documents, requested)
            if not selected:
                return _print_diff(compare_catalog(args.source, documents, [], [], selected), args.json)
        if args.command in {"dump", "diff"}:
            prefix = f"WARDEN_{args.source.upper()}"
            url, api_key = os.getenv(f"{prefix}_URL", ""), os.getenv(f"{prefix}_API_KEY", "")
            if not url or not api_key:
                raise ValueError(f"{prefix}_URL and {prefix}_API_KEY are required")
            if args.command == "diff":
                profiles, formats = asyncio.run(read_arr(args.source, url, api_key))
                try:
                    report = compare_catalog(args.source, documents, profiles, formats, selected)
                except (KeyError, TypeError) as exc:
                    raise ValueError("Arr response has an unsupported or incomplete profile structure") from exc
                return _print_diff(report, args.json)
            else:
                documents = asyncio.run(dump(args.source, url, api_key, args.profile))
                write_catalog(args.output, documents)
        else:
            documents = load_catalog(args.directory)
    except httpx.HTTPStatusError as exc:
        print(f"error: Arr returned HTTP {exc.response.status_code}; {args.command} did not complete", file=sys.stderr)
        return 1
    except httpx.RequestError:
        print(f"error: Arr request failed; {args.command} did not complete", file=sys.stderr)
        return 1
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    profiles = sum(len(d.data["quality_profiles"]) for d in documents if d.kind == "profiles")
    formats = sum(d.kind == "custom_formats" for d in documents)
    if args.command == "dump":
        print(f"Exported {profiles} profiles and {formats} custom formats.")
    else:
        print(f"Valid catalog: {profiles} profiles, {formats} custom formats.")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Compatibility entry point for the original profile-only module command."""
    parser = argparse.ArgumentParser(prog="warden-profiles")
    configure_parser(parser)
    return run(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
