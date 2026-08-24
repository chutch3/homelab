"""ghcr version retention — the `ci gc` logic.

Per-commit ``:sha`` builds accumulate one version per main commit. This prunes
the stale ones (sha-only or untagged, older than a cutoff) while keeping releases
(semver tags) and the moving ``:latest`` / ``:main`` tags.

:func:`versions_to_prune` is pure; :class:`RegistryGc` takes the clock and the
command runner, so its tests fix "now" and assert on the gh calls it would make.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from ci.adapters import Clock, CommandRunner, Console
from ci.affected import UnitCatalog

_SEMVER = re.compile(r"^\d+\.\d+\.\d+")
_KEEP_TAGS = {"latest", "main"}


def _is_release(tags: list[str]) -> bool:
    """A version worth keeping regardless of age: a release or a moving tag."""
    return any(t in _KEEP_TAGS or _SEMVER.match(t) for t in tags)


def _created_ts(version: dict) -> float:
    return datetime.fromisoformat(version["created_at"].replace("Z", "+00:00")).timestamp()


def versions_to_prune(versions: list[dict], now_ts: float, cutoff_days: int = 14) -> list:
    """IDs of versions to delete: not a release/moving tag, and older than the cutoff."""
    cutoff = now_ts - cutoff_days * 86400
    prune = []
    for v in versions:
        tags = (v.get("metadata", {}).get("container", {}) or {}).get("tags") or []
        if _is_release(tags):
            continue
        if _created_ts(v) < cutoff:
            prune.append(v["id"])
    return prune


class RegistryGc:
    """Lists each buildable image's stale ghcr versions and (optionally) deletes them."""

    def __init__(
        self,
        catalog: UnitCatalog,
        commands: CommandRunner,
        clock: Clock,
        console: Console,
    ) -> None:
        self._catalog = catalog
        self._commands = commands
        self._clock = clock
        self._console = console

    def prune(self, cutoff_days: int = 14, apply: bool = False) -> int:
        """Dry-run by default. Uses the local ``gh`` CLI auth (read+delete:packages).

        Returns the number of versions pruned (or that would be).
        """
        now_ts = self._clock.now_timestamp()
        total = 0
        for image in self._catalog.image_names():
            versions = self._gh_json(
                ["--paginate", f"/user/packages/container/{image}/versions"]
            )
            for vid in versions_to_prune(versions, now_ts, cutoff_days):
                total += 1
                if apply:
                    self._commands.run(
                        ["gh", "api", "-X", "DELETE",
                         f"/user/packages/container/{image}/versions/{vid}"],
                        check=True,
                    )
                    self._console.out(f"{image}: deleted version {vid}")
                else:
                    self._console.out(f"{image}: [dry-run] would delete version {vid}")
        self._console.out(f"{'Pruned' if apply else 'Would prune'} {total} version(s).")
        return total

    def _gh_json(self, args: list[str]) -> list:
        result = self._commands.run(["gh", "api", *args], capture=True, check=True)
        return json.loads(result.stdout or "[]")
