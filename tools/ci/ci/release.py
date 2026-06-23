"""Per-app (per-image) release helpers — the `ci release` logic.

A release is cut by pushing a git tag ``<image_name>-vX.Y.Z`` (e.g.
``warden-v1.2.0``, ``takeout-worker-v0.3.1``). The release workflow promotes the
already-built ``:<sha>`` image to ``:X.Y.Z`` (no rebuild) and bumps the compose pin.

Parsing is the fiddly part — image names themselves contain hyphens and digits
(``takeout-manager``, ``iperf3-server``), so the version is split on the last
``-v`` that is followed by a digit.
"""

from __future__ import annotations

import os
import re

from ci.affected import Unit, discover_units

# <image>-vX.Y.Z (with optional pre-release/build suffix). `.+` is greedy so the
# split lands on the last `-vX.Y.Z`, keeping hyphenated image names intact.
_TAG_RE = re.compile(r"^(?P<image>.+)-v(?P<version>\d+\.\d+\.\d+(?:[-+.]\S+)?)$")


def parse_release_tag(tag: str) -> tuple[str, str] | None:
    """``warden-v1.2.0`` -> ``("warden", "1.2.0")``; ``None`` if not a release tag."""
    match = _TAG_RE.match(tag or "")
    if not match:
        return None
    return match.group("image"), match.group("version")


def resolve_unit(image_name: str, units: list[Unit]) -> Unit | None:
    """The buildable unit that produces ``image_name`` (or ``None``)."""
    return next((u for u in units if u.image_name == image_name), None)


def release_info(repo_root: str | os.PathLike[str], tag: str) -> dict | None:
    """Resolve a release tag to its image/version/unit, or ``None`` if not a
    valid release tag for a known buildable image."""
    parsed = parse_release_tag(tag)
    if not parsed:
        return None
    image_name, version = parsed
    unit = resolve_unit(image_name, discover_units(repo_root))
    if not unit:
        return None
    return {"version": version, **unit.as_dict()}
