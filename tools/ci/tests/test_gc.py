"""Tests for ghcr version retention (the `ci gc` selection logic).

The pure function decides which container *versions* to prune: stale per-commit
(:sha) or untagged builds, while keeping releases (semver tags) and the moving
:latest / :main tags. :class:`RegistryGc` is driven through a fake command
runner and a fixed clock, so the gh calls are asserted without a network.
"""

from __future__ import annotations

from datetime import datetime, timezone

import json

import pytest

from ci.adapters import CommandResult
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


class TestRegistryGc:
    """`RegistryGc.prune` — what it asks gh for, and what it deletes."""

    IMAGE_COMPOSE = (
        "services:\n  warden:\n    image: ghcr.io/ns/warden:latest\n"
        "    build: { context: ., dockerfile: Dockerfile }\n"
    )

    @pytest.fixture
    def subject(self, container, filesystem, clock):
        filesystem.files["stacks/apps/warden/docker-compose.yml"] = self.IMAGE_COMPOSE
        clock.timestamp = NOW
        return container.registry_gc()

    def _listing(self, versions):
        return CommandResult(0, stdout=json.dumps(versions))

    def test_lists_versions_for_every_buildable_image(self, subject, commands):
        commands._results = [self._listing([])]
        subject.prune()
        assert commands.argvs[0] == [
            "gh", "api", "--paginate", "/user/packages/container/warden/versions"
        ]

    def test_a_dry_run_deletes_nothing_and_says_so(self, subject, commands, console):
        commands._results = [self._listing([_v(4, 30, ["oldsha"])])]
        assert subject.prune() == 1
        assert commands.argvs == [
            ["gh", "api", "--paginate", "/user/packages/container/warden/versions"]
        ]
        assert console.stdout[-1] == "Would prune 1 version(s)."
        assert "[dry-run] would delete version 4" in console.text

    def test_apply_issues_a_delete_per_stale_version(self, subject, commands, console):
        commands._results = [self._listing([_v(4, 30, ["oldsha"]), _v(6, 30, [])])]
        assert subject.prune(apply=True) == 2
        assert commands.argvs[1:] == [
            ["gh", "api", "-X", "DELETE", "/user/packages/container/warden/versions/4"],
            ["gh", "api", "-X", "DELETE", "/user/packages/container/warden/versions/6"],
        ]
        assert console.stdout[-1] == "Pruned 2 version(s)."

    def test_a_release_version_is_never_deleted(self, subject, commands):
        commands._results = [self._listing([_v(1, 900, ["1.2.0"])])]
        assert subject.prune(apply=True) == 0
        assert len(commands.argvs) == 1  # the listing only

    def test_the_cutoff_is_honoured(self, subject, commands):
        commands._results = [self._listing([_v(4, 30, ["oldsha"])])]
        assert subject.prune(cutoff_days=60) == 0

    def test_an_empty_body_is_treated_as_no_versions(self, subject, commands):
        commands._results = [CommandResult(0, stdout="")]
        assert subject.prune() == 0
