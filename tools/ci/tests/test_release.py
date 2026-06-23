"""Tests for release-tag parsing and resolution (the `ci release` logic)."""

from __future__ import annotations

import pytest

import textwrap
from pathlib import Path

from ci.affected import Unit
from ci.release import parse_release_tag, release_info, resolve_unit


@pytest.mark.parametrize(
    "tag,expected",
    [
        ("warden-v1.2.0", ("warden", "1.2.0")),
        ("takeout-manager-v0.3.1", ("takeout-manager", "0.3.1")),  # hyphenated image
        ("takeout-worker-v2.0.0", ("takeout-worker", "2.0.0")),
        ("iperf3-server-v1.0.0", ("iperf3-server", "1.0.0")),  # digit in image name
        ("homelab-devbox-v3.4.5", ("homelab-devbox", "3.4.5")),
        ("warden-v1.2.0-rc1", ("warden", "1.2.0-rc1")),  # pre-release suffix
    ],
)
def test_parse_valid_release_tags(tag, expected):
    assert parse_release_tag(tag) == expected


@pytest.mark.parametrize(
    "tag",
    [
        "v1.2.0",  # no image
        "warden-1.2.0",  # missing the v
        "random-tag",
        "warden-vX.Y.Z",  # version must start with a digit
        "warden-v1",  # not full X.Y.Z
        "warden-v1.2",  # not full X.Y.Z
        "",
    ],
)
def test_parse_rejects_non_release_tags(tag):
    assert parse_release_tag(tag) is None


def _unit(image_name):
    return Unit(
        service=image_name,
        image=f"ghcr.io/ns/{image_name}:latest",
        stack_dir=f"stacks/apps/{image_name}",
        context=f"stacks/apps/{image_name}",
        dockerfile=None,
        compose_file=f"stacks/apps/{image_name}/docker-compose.yml",
        watch=(),
    )


def test_resolve_unit_matches_by_image_name():
    units = [_unit("warden"), _unit("homelab-devbox")]
    assert resolve_unit("homelab-devbox", units).service == "homelab-devbox"


def test_resolve_unit_returns_none_when_no_match():
    assert resolve_unit("nope", [_unit("warden")]) is None


def _write_repo(tmp_path):
    (tmp_path / "stacks/apps/warden").mkdir(parents=True)
    (tmp_path / "stacks/apps/warden/docker-compose.yml").write_text(
        textwrap.dedent(
            """
            services:
              warden:
                image: ${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE:-ns}/warden:latest
                build: { context: ., dockerfile: app/Dockerfile }
            """
        )
    )
    return tmp_path


def test_release_info_resolves_tag_to_unit(tmp_path):
    _write_repo(tmp_path)
    info = release_info(tmp_path, "warden-v1.4.0")
    assert info["image_name"] == "warden"
    assert info["version"] == "1.4.0"
    assert info["compose_file"] == "stacks/apps/warden/docker-compose.yml"
    assert info["service"] == "warden"


def test_release_info_none_for_unknown_image(tmp_path):
    _write_repo(tmp_path)
    assert release_info(tmp_path, "ghost-v1.0.0") is None


def test_release_info_none_for_non_release_tag(tmp_path):
    _write_repo(tmp_path)
    assert release_info(tmp_path, "not-a-release") is None
