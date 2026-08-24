"""Unit tests for the monorepo change-detection logic.

The pure functions (``affected_units``, ``dedupe_by_image``, ``tooling_changed``)
are exercised with hand-built ``Unit`` lists; :class:`UnitCatalog` reads through
a fake filesystem, so discovery is asserted without writing any files.
"""

from __future__ import annotations

import textwrap

import pytest

from ci.affected import (
    Unit,
    UnitCatalog,
    affected_units,
    dedupe_by_image,
    tooling_changed,
)
from conftest import ROOT, FakeFileSystem


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


def test_templated_tag_with_default_is_stripped():
    # The deploy pin is ${IMAGE_TAG:-3.20.0} — its ':-' colon must not be mistaken
    # for the name:tag separator (which is the first colon after the last '/').
    u = _unit(
        "warden",
        "${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE:-chutch3}/warden:${IMAGE_TAG:-3.20.0}",
        "stacks/apps/warden",
        ["stacks/apps/warden/**"],
    )
    assert u.image_name == "warden"
    assert u.image_key == "${REGISTRY:-ghcr.io}/${REGISTRY_NAMESPACE:-chutch3}/warden"


def test_tooling_change_flags_everything():
    assert tooling_changed(["tools/ci/ci/affected.py"]) is True
    assert tooling_changed([".github/workflows/build.yml"]) is True
    assert tooling_changed(["stacks/apps/warden/app/main.py"]) is False


class TestUnitCatalog:
    """`UnitCatalog` — discovery, the build matrix and the image list, over a fake tree."""

    @pytest.fixture
    def subject(self, container):
        return container.catalog()

    def _seed(self, filesystem, path: str, compose: str) -> None:
        filesystem.files[path] = textwrap.dedent(compose)

    def test_reads_build_and_defaults_watch_to_the_stack_dir(self, subject, filesystem):
        self._seed(filesystem, "stacks/apps/warden/docker-compose.yml", """
            services:
              warden:
                image: ghcr.io/ns/warden:1.4.0
                build:
                  context: .
                  dockerfile: app/Dockerfile
            """)
        units = subject.units()
        assert len(units) == 1
        assert units[0].service == "warden"
        assert units[0].context == "stacks/apps/warden"
        assert units[0].dockerfile == "app/Dockerfile"
        assert units[0].watch == ("stacks/apps/warden/**",)

    def test_honours_explicit_watch_and_skips_services_without_build(self, subject, filesystem):
        self._seed(filesystem, "stacks/apps/code-server/docker-compose.yml", """
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
            """)
        units = subject.units()
        assert [u.service for u in units] == ["code-server"]  # sidecar has no build:
        assert units[0].context == "images/devbox"  # ../../../ resolved repo-relative
        assert set(units[0].watch) == {"stacks/apps/code-server/**", "images/devbox/**"}

    def test_finds_nested_non_apps_compose(self, subject, filesystem):
        # The monitoring stack lives at stacks/monitoring/docker-compose.yml.
        self._seed(filesystem, "stacks/monitoring/docker-compose.yml", """
            services:
              prometheus:
                image: prom/prometheus:v2.55.0
              iperf3-exporter:
                image: ghcr.io/ns/iperf3-exporter:latest
                build: { context: custom-exporter, dockerfile: custom-exporter/Dockerfile }
                x-homelab:
                  watch: [stacks/monitoring/custom-exporter/**]
            """)
        units = subject.units()
        assert [u.service for u in units] == ["iperf3-exporter"]
        assert units[0].context == "stacks/monitoring/custom-exporter"

    def test_multiple_images_per_app(self, subject, filesystem):
        self._seed(filesystem, "stacks/apps/takeout-manager/docker-compose.yml", """
            services:
              manager:
                image: ghcr.io/ns/takeout-manager:2.0.0
                build: { context: manager, dockerfile: manager/Dockerfile }
              worker:
                image: ghcr.io/ns/takeout-worker:2.0.0
                build: { context: worker, dockerfile: worker/Dockerfile }
            """)
        assert sorted(u.service for u in subject.units()) == ["manager", "worker"]
        assert {u.context for u in subject.units()} == {
            "stacks/apps/takeout-manager/manager",
            "stacks/apps/takeout-manager/worker",
        }

    def test_unparseable_compose_is_skipped_not_fatal(self, subject, filesystem):
        self._seed(filesystem, "stacks/apps/broken/docker-compose.yml", "services: [\n unclosed\n")
        self._seed(filesystem, "stacks/apps/warden/docker-compose.yml", """
            services:
              warden:
                image: ghcr.io/ns/warden:1.4.0
                build: { context: ., dockerfile: Dockerfile }
            """)
        assert [u.service for u in subject.units()] == ["warden"]

    def test_image_names_dedupe_and_sort(self, subject, filesystem):
        for name, img in [("warden", "warden"), ("code-server", "homelab-devbox"),
                          ("claudecodeui", "homelab-devbox")]:
            self._seed(filesystem, f"stacks/apps/{name}/docker-compose.yml", f"""
                services:
                  {name}:
                    image: ghcr.io/ns/{img}:latest
                    build: {{ context: ., dockerfile: Dockerfile }}
                """)
        # homelab-devbox appears twice (two consumers) -> deduped to one entry.
        assert subject.image_names() == ["homelab-devbox", "warden"]

    def test_matrix_selects_only_the_affected_unit(self, subject, filesystem):
        for name in ("warden", "fiber"):
            self._seed(filesystem, f"stacks/apps/{name}/docker-compose.yml", f"""
                services:
                  {name}:
                    image: ghcr.io/ns/{name}:1.0.0
                    build: {{ context: ., dockerfile: Dockerfile }}
                """)
        matrix = subject.matrix(["stacks/apps/warden/app/main.py"])
        assert [e["image_name"] for e in matrix] == ["warden"]

    def test_a_tooling_change_puts_every_unit_in_the_matrix(self, subject, filesystem):
        for name in ("warden", "fiber"):
            self._seed(filesystem, f"stacks/apps/{name}/docker-compose.yml", f"""
                services:
                  {name}:
                    image: ghcr.io/ns/{name}:1.0.0
                    build: {{ context: ., dockerfile: Dockerfile }}
                """)
        matrix = subject.matrix(["tools/ci/ci/affected.py"])
        assert sorted(e["image_name"] for e in matrix) == ["fiber", "warden"]


class TestFakeFileSystemFidelity:
    """The fake must glob the way the real one does, or every test above lies."""

    def test_discovery_globs_agree_with_the_real_filesystem_on_this_repo(
        self, repo_container, filesystem
    ):
        from ci.adapters import FileSystem
        from ci.affected import DISCOVERY_GLOBS
        from conftest import REPO_ROOT

        real = FileSystem()
        for pattern in DISCOVERY_GLOBS:
            found = real.glob(REPO_ROOT, pattern)
            rels = {p.relative_to(REPO_ROOT).as_posix() for p in found}
            fake = FakeFileSystem({r: "" for r in rels}, root=REPO_ROOT)
            assert {p.relative_to(REPO_ROOT).as_posix() for p in fake.glob(REPO_ROOT, pattern)} == rels
