"""
tranga_manga_volume_resolver.core

Pure logic for mapping MangaDex volume data to Tranga chapter file paths.
No I/O. No side effects.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Chapter:
    key: str
    chapter_number: str
    volume_number: Optional[int]
    filename: str


@dataclass(frozen=True)
class Migration:
    key: str
    old_filename: str
    new_filename: str
    volume: int


def parse_mangadex_aggregate(data: dict) -> dict[str, str]:
    """Return a mapping of chapter_number -> volume_string from a MangaDex aggregate response."""
    result: dict[str, str] = {}
    for volume_entry in data.get("volumes", {}).values():
        volume = volume_entry["volume"]
        for chapter_entry in volume_entry.get("chapters", {}).values():
            result[chapter_entry["chapter"]] = volume
    return result


def compute_target_path(manga_name: str, chapter_number: str, volume: Optional[str]) -> str:
    """Return the relative target path for a chapter archive."""
    filename = f"{manga_name} - Ch.{chapter_number}.cbz"
    if volume is None or volume == "none":
        return filename
    return os.path.join(f"{manga_name} Vol {volume}", filename)


def plan_migrations(
    manga_name: str,
    chapters: list[Chapter],
    volume_map: dict[str, str],
) -> list[Migration]:
    """Return the list of chapters that need to be moved to a volume subdirectory."""
    migrations: list[Migration] = []
    for chapter in chapters:
        volume_str = volume_map.get(chapter.chapter_number)
        if volume_str is None or volume_str == "none":
            continue
        target = compute_target_path(manga_name, chapter.chapter_number, volume_str)
        if chapter.filename == target:
            continue
        migrations.append(Migration(
            key=chapter.key,
            old_filename=chapter.filename,
            new_filename=target,
            volume=int(volume_str),
        ))
    return migrations
