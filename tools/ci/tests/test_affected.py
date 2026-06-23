"""Unit tests for the monorepo change-detection logic.

The pure functions (``affected_units``, ``dedupe_by_image``, ``tooling_changed``)
are exercised with hand-built ``Unit`` lists; ``discover_units`` is exercised
against compose files written into a tmp repo.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from ci.affected import (
    Unit,
    affected_units,
    dedupe_by_image,
    discover_units,
    tooling_changed,
)


def _unit(service, image, stack_dir, watch):
    return Unit(
        service=service,
        image=image,
        stack_dir=stack_dir,
        context=stack_dir,
        dockerfile=None,
        compose_file=f"{stack_dir}/docker-compose.yml",
        watch=tuple(watch),
    )


WARDEN = _unit("warden", "ghcr.io/ns/warden:1.4.0", "stacks/apps/warden", ["stacks/apps/warden/**"])
FIBER = _unit("fiber", "ghcr.io/ns/fiber:0.9.0", "stacks/apps/fiber", ["stacks/apps/fiber/**"])
CODE = _unit(
    "code-server",
    "ghcr.io/ns/homelab-devbox:1.2.0",
    "stacks/apps/code-server",
    ["stacks/apps/code-server/**", "images/devbox/**"],
)
CLAUDE = _unit(
    "claudecodeui",
    "ghcr.io/ns/homelab-devbox:1.2.0",
    "stacks/apps/claudecodeui",
    ["stacks/apps/claudecodeui/**", "images/devbox/**"],
)
ALL = [WARDEN, FIBER, CODE, CLAUDE]


def _services(units):
    return sorted(u.service for u in units)


def test_change_in_one_app_affects_only_that_app():
    assert _services(affected_units(["stacks/apps/warden/app/main.py"], ALL)) == ["warden"]


def test_unrelated_change_affects_nothing():
    assert affected_units(["README.md", "docs/index.md"], ALL) == []


def test_shared_dockerfile_fans_out_to_all_consumers():
    # The headline requirement: one changed file → multiple units.
    affected = affected_units(["images/devbox/Dockerfile"], ALL)
    assert _services(affected) == ["claudecodeui", "code-server"]


def test_dedupe_collapses_units_building_the_same_image():
    affected = affected_units(["images/devbox/Dockerfile"], ALL)
    deduped = dedupe_by_image(affected)
    assert len(deduped) == 1
    assert deduped[0].image_key == "ghcr.io/ns/homelab-devbox"


def test_distinct_images_are_not_deduped():
    deduped = dedupe_by_image([WARDEN, FIBER])
    assert _services(deduped) == ["fiber", "warden"]


def test_image_key_strips_tag_and_digest():
    assert WARDEN.image_key == "ghcr.io/ns/warden"
    pinned = _unit("x", "ghcr.io/ns/x:1.0@sha256:abc", "stacks/apps/x", ["stacks/apps/x/**"])
    assert pinned.image_key == "ghcr.io/ns/x"


def test_registry_port_is_not_mistaken_for_a_tag():
    u = _unit("x", "registry:5000/ns/x:1.0", "stacks/apps/x", ["stacks/apps/x/**"])
    assert u.image_key == "registry:5000/ns/x"


def test_list_images_dedupes_and_sorts(tmp_path):
    from ci.affected import list_images

    for name, img in [("warden", "warden"), ("code-server", "homelab-devbox"),
                      ("claudecodeui", "homelab-devbox")]:
        d = tmp_path / "stacks/apps" / name
        d.mkdir(parents=True)
        (d / "docker-compose.yml").write_text(
            f"services:\n  {name}:\n    image: ghcr.io/ns/{img}:latest\n"
            f"    build: {{ context: ., dockerfile: Dockerfile }}\n"
        )
    # homelab-devbox appears twice (two consumers) -> deduped to one entry.
    assert list_images(tmp_path) == ["homelab-devbox", "warden"]


def test_image_name_is_bare_last_segment():
    assert WARDEN.image_name == "warden"
    assert CODE.image_name == "homelab-devbox"
    templated = _unit(
        "warden",
        "${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE:-chutch3}/warden:latest",
        "stacks/apps/warden",
        ["stacks/apps/warden/**"],
    )
    assert templated.image_name == "warden"


def test_tooling_change_flags_everything():
    assert tooling_changed(["tools/ci/ci/affected.py"]) is True
    assert tooling_changed([".github/workflows/build.yml"]) is True
    assert tooling_changed(["stacks/apps/warden/app/main.py"]) is False


# --- discovery against a tmp repo -------------------------------------------------


def _write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content))


def test_discover_reads_build_and_defaults_watch_to_stack_dir(tmp_path):
    _write(
        tmp_path / "stacks/apps/warden/docker-compose.yml",
        """
        services:
          warden:
            image: ghcr.io/ns/warden:1.4.0
            build:
              context: .
              dockerfile: app/Dockerfile
        """,
    )
    units = discover_units(tmp_path)
    assert len(units) == 1
    u = units[0]
    assert u.service == "warden"
    assert u.context == "stacks/apps/warden"
    assert u.dockerfile == "app/Dockerfile"
    assert u.watch == ("stacks/apps/warden/**",)  # default


def test_discover_honours_explicit_watch_and_skips_services_without_build(tmp_path):
    _write(
        tmp_path / "stacks/apps/code-server/docker-compose.yml",
        """
        services:
          code-server:
            image: ghcr.io/ns/homelab-devbox:1.2.0
            build:
              context: ../../../images/devbox
              dockerfile: Dockerfile
            x-homelab:
              watch:
                - stacks/apps/code-server/**
                - images/devbox/**
          sidecar:
            image: redis:7
        """,
    )
    units = discover_units(tmp_path)
    assert [u.service for u in units] == ["code-server"]  # sidecar has no build:
    u = units[0]
    assert u.context == "images/devbox"  # ../../../ resolved repo-relative
    assert set(u.watch) == {"stacks/apps/code-server/**", "images/devbox/**"}


def test_discover_finds_nested_non_apps_compose(tmp_path):
    # The monitoring stack lives at stacks/monitoring/docker-compose.yml (not under
    # stacks/apps), and only its build: services should become units.
    _write(
        tmp_path / "stacks/monitoring/docker-compose.yml",
        """
        services:
          prometheus:
            image: prom/prometheus:v2.55.0
          iperf3-exporter:
            image: ghcr.io/ns/iperf3-exporter:latest
            build: { context: custom-exporter, dockerfile: custom-exporter/Dockerfile }
            x-homelab:
              watch: [stacks/monitoring/custom-exporter/**]
        """,
    )
    units = discover_units(tmp_path)
    assert [u.service for u in units] == ["iperf3-exporter"]
    assert units[0].context == "stacks/monitoring/custom-exporter"


def test_discover_multiple_images_per_app(tmp_path):
    _write(
        tmp_path / "stacks/apps/takeout-manager/docker-compose.yml",
        """
        services:
          manager:
            image: ghcr.io/ns/takeout-manager:2.0.0
            build: { context: manager, dockerfile: manager/Dockerfile }
          worker:
            image: ghcr.io/ns/takeout-worker:2.0.0
            build: { context: worker, dockerfile: worker/Dockerfile }
        """,
    )
    units = discover_units(tmp_path)
    assert sorted(u.service for u in units) == ["manager", "worker"]
    assert {u.context for u in units} == {
        "stacks/apps/takeout-manager/manager",
        "stacks/apps/takeout-manager/worker",
    }
