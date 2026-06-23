"""Change detection for the homelab monorepo build pipeline.

A *unit* is a docker-compose service that declares a ``build:`` section. Given the
set of files a change touched, :func:`affected_units` returns every unit whose
``x-homelab.watch`` globs match — many-to-many on purpose, so one shared file
(e.g. ``images/devbox/Dockerfile``) flags every consumer that watches it.

Discovery (YAML I/O) lives in :func:`discover_units`; matching is the pure
function :func:`affected_units` so it can be unit-tested with plain data.
"""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Roots walked for buildable units — recursive, so the monitoring stack
# (stacks/monitoring/docker-compose.yml) and any nested compose are covered.
# Only services that declare build: become units, so scanning broadly is safe.
DISCOVERY_GLOBS = ("stacks/**/docker-compose.yml", "images/**/docker-compose.yml")

# A change to any of these affects every unit (build logic / shared CI), so the
# caller should treat a match here as "build everything".
TOOLING_GLOBS = (
    "tools/ci/**",
    ".github/workflows/build.yml",
)


@dataclass(frozen=True)
class Unit:
    """One buildable image: a compose service with a ``build:`` section."""

    service: str
    image: str
    stack_dir: str  # repo-relative dir of the compose file
    context: str  # repo-relative build context
    dockerfile: str | None
    compose_file: str  # repo-relative
    watch: tuple[str, ...] = field(default_factory=tuple)  # repo-relative globs

    @property
    def image_key(self) -> str:
        """Image ref without tag/digest — the dedup key when two units build the same image."""
        return _image_key(self.image)

    @property
    def image_name(self) -> str:
        """Bare image name (last path segment), e.g. ``warden`` or ``homelab-devbox``."""
        return self.image_key.rsplit("/", 1)[-1]

    def as_dict(self) -> dict:
        """JSON-serializable view shared by the build matrix and release resolution."""
        return {
            "service": self.service,
            "image_name": self.image_name,
            "context": self.context,
            "dockerfile": self.dockerfile,
            "compose_file": self.compose_file,
            "stack_dir": self.stack_dir,
        }


def _image_key(image: str) -> str:
    image = image.split("@", 1)[0]  # drop @sha256:... digest
    slash = image.rfind("/")
    colon = image.rfind(":")
    if colon > slash:  # a tag (not a registry :port, which sits before the last /)
        image = image[:colon]
    return image


def _norm(path: str) -> str:
    return os.path.normpath(path).replace(os.sep, "/")


def _match(path: str, glob: str) -> bool:
    """Match a repo-relative path against a watch glob, treating ``/**`` as a subtree."""
    if glob.endswith("/**"):
        prefix = glob[:-3]
        return path == prefix or path.startswith(prefix + "/")
    return fnmatch.fnmatch(path, glob)


def discover_units(repo_root: str | os.PathLike[str]) -> list[Unit]:
    """Parse every compose file under the discovery roots into a list of :class:`Unit`."""
    root = Path(repo_root)
    units: list[Unit] = []
    for pattern in DISCOVERY_GLOBS:
        for compose_path in sorted(root.glob(pattern)):
            try:
                data = yaml.safe_load(compose_path.read_text()) or {}
            except yaml.YAMLError:
                continue
            stack_dir = _norm(str(compose_path.parent.relative_to(root)))
            for name, svc in (data.get("services") or {}).items():
                if not isinstance(svc, dict) or "build" not in svc:
                    continue
                build = svc["build"]
                if isinstance(build, str):
                    context, dockerfile = build, None
                else:
                    context = build.get("context", ".")
                    dockerfile = build.get("dockerfile")
                context_repo = _norm(os.path.join(stack_dir, context))
                homelab = svc.get("x-homelab") or {}
                watch = tuple(homelab.get("watch") or [f"{stack_dir}/**"])
                units.append(
                    Unit(
                        service=name,
                        image=svc.get("image", ""),
                        stack_dir=stack_dir,
                        context=context_repo,
                        dockerfile=dockerfile,
                        compose_file=_norm(str(compose_path.relative_to(root))),
                        watch=watch,
                    )
                )
    return units


def affected_units(changed_files: list[str], units: list[Unit]) -> list[Unit]:
    """Return every unit with a ``watch`` glob matching any changed file (many-to-many)."""
    changed = [_norm(f) for f in changed_files]
    return [
        unit
        for unit in units
        if any(_match(path, glob) for glob in unit.watch for path in changed)
    ]


def tooling_changed(changed_files: list[str]) -> bool:
    """True if a change touches build tooling (→ caller should build everything)."""
    changed = [_norm(f) for f in changed_files]
    return any(_match(path, glob) for glob in TOOLING_GLOBS for path in changed)


def dedupe_by_image(units: list[Unit]) -> list[Unit]:
    """Collapse units that build the same image ref (build once, e.g. the devbox consumers)."""
    seen: dict[str, Unit] = {}
    for unit in units:
        seen.setdefault(unit.image_key, unit)
    return list(seen.values())


def compute_matrix(repo_root: str | os.PathLike[str], changed_files: list[str]) -> list[dict]:
    """The deduped build matrix (one entry per image) for a set of changed files."""
    units = discover_units(repo_root)
    selected = units if tooling_changed(changed_files) else affected_units(changed_files, units)
    return [u.as_dict() for u in dedupe_by_image(selected)]


def list_images(repo_root: str | os.PathLike[str]) -> list[str]:
    """Every buildable image name (deduped, sorted) — used to promote all images on release."""
    return sorted({u.image_name for u in discover_units(repo_root)})
