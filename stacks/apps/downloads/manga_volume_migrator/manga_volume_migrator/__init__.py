"""
manga_volume_migrator

Migrate Tranga manga chapter files into volume subdirectories using
MangaDex volume data. Tranga handles the physical file move and DB update
atomically via PATCH /v2/Chapters/{id}.
"""
from __future__ import annotations

import sys

from manga_volume_migrator.clients import MangaDexClient, TrangaClient
from manga_volume_migrator.core import parse_mangadex_aggregate, plan_migrations


def migrate(
    manga_name: str,
    manga_id: str,
    mangadex_uuid: str,
    mangadex_client: MangaDexClient,
    tranga_client: TrangaClient,
    dry_run: bool = False,
) -> int:
    """
    Reorganise chapter files for one manga into volume subdirectories.

    Fetches volume data from MangaDex, computes which chapters need moving,
    and calls Tranga to update each chapter (Tranga moves the file and updates
    its database atomically).

    Returns the number of errors encountered.
    """
    aggregate = mangadex_client.fetch_aggregate(mangadex_uuid)
    volume_map = parse_mangadex_aggregate(aggregate)

    chapters = tranga_client.get_chapters(manga_id)
    migrations = plan_migrations(manga_name, chapters, volume_map)

    if dry_run:
        for m in migrations:
            print(f"[dry-run] {m.old_filename} -> {m.new_filename}", file=sys.stdout)
        return 0

    errors = 0
    for m in migrations:
        try:
            tranga_client.update_chapter(m.key, m.new_filename, m.volume)
        except Exception as exc:
            print(f"[error] failed to update chapter {m.key} in Tranga: {exc}", file=sys.stderr)
            errors += 1

    return errors
