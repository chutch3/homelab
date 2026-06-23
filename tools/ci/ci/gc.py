"""ghcr version retention — the `ci gc` logic.

Per-commit ``:sha`` builds accumulate one version per main commit. This prunes
the stale ones (sha-only or untagged, older than a cutoff) while keeping releases
(semver tags) and the moving ``:latest`` / ``:main`` tags.

:func:`versions_to_prune` is pure and unit-tested; :func:`prune` is the gh-CLI
I/O wrapper (lists image names from the compose units, lists/deletes versions).
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone

from ci.affected import discover_units

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


def _gh_json(args: list[str]) -> list:
    out = subprocess.run(["gh", "api", *args], capture_output=True, text=True, check=True).stdout
    return json.loads(out or "[]")


def prune(repo_root: str, cutoff_days: int = 14, apply: bool = False, runner=subprocess.run) -> int:
    """List each buildable image's stale versions and (optionally) delete them.

    Dry-run by default. Uses the local ``gh`` CLI auth (needs read:packages +
    delete:packages). Returns the number of versions pruned (or that would be).
    """
    images = sorted({u.image_name for u in discover_units(repo_root)})
    now_ts = datetime.now(tz=timezone.utc).timestamp()
    total = 0
    for image in images:
        versions = _gh_json(["--paginate", f"/user/packages/container/{image}/versions"])
        ids = versions_to_prune(versions, now_ts, cutoff_days)
        for vid in ids:
            total += 1
            if apply:
                runner(["gh", "api", "-X", "DELETE",
                        f"/user/packages/container/{image}/versions/{vid}"], check=True)
                print(f"{image}: deleted version {vid}")
            else:
                print(f"{image}: [dry-run] would delete version {vid}")
    print(f"{'Pruned' if apply else 'Would prune'} {total} version(s).")
    return total
