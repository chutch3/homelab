"""Tests for ghcr version retention (the `ci gc` selection logic).

The pure function decides which container *versions* to prune: stale per-commit
(:sha) or untagged builds, while keeping releases (semver tags) and the moving
:latest / :main tags. Only this selection is unit-tested; the gh API I/O is glue.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ci.gc import versions_to_prune

NOW = datetime(2026, 6, 23, tzinfo=timezone.utc).timestamp()


def _v(id, days_ago, tags):
    created = datetime(2026, 6, 23, tzinfo=timezone.utc).timestamp() - days_ago * 86400
    iso = datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {"id": id, "created_at": iso, "metadata": {"container": {"tags": tags}}}


def test_keeps_releases_latest_main_and_recent_prunes_stale_sha_and_untagged():
    versions = [
        _v(1, 60, ["1.2.0"]),  # semver release -> keep (even if old)
        _v(2, 60, ["latest", "abc123"]),  # latest -> keep
        _v(3, 60, ["main"]),  # main -> keep
        _v(4, 30, ["oldsha456"]),  # stale sha-only -> prune
        _v(5, 2, ["recentsha"]),  # recent sha -> keep
        _v(6, 30, []),  # old untagged -> prune
    ]
    assert versions_to_prune(versions, NOW, cutoff_days=14) == [4, 6]


def test_nothing_pruned_when_all_recent():
    versions = [_v(1, 1, ["sha1"]), _v(2, 5, [])]
    assert versions_to_prune(versions, NOW, cutoff_days=14) == []


def test_semver_with_prerelease_is_kept():
    versions = [_v(1, 90, ["2.0.0-rc1"])]
    assert versions_to_prune(versions, NOW, cutoff_days=14) == []


def test_cutoff_boundary_is_exclusive_of_recent():
    # exactly at the cutoff edge: 14 days old with only a sha tag -> pruned
    assert versions_to_prune([_v(1, 15, ["s"])], NOW, cutoff_days=14) == [1]
    assert versions_to_prune([_v(1, 13, ["s"])], NOW, cutoff_days=14) == []
