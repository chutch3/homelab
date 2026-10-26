from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol


@dataclass(frozen=True)
class Document:
    source: Literal["radarr", "sonarr"]
    kind: Literal["profiles", "custom_formats"]
    path: str
    data: dict[str, Any]


@dataclass(frozen=True)
class Snapshot:
    commit: str
    documents: tuple[Document, ...]


class CatalogSource(Protocol):
    async def fetch(self) -> Snapshot: ...


def validate_references(documents: Sequence[Document]) -> None:
    """Check relationships after document structure has been schema-validated."""
    profiles: dict[tuple[str, str], str] = {}
    formats: dict[tuple[str, str], str] = {}
    for document in documents:
        objects = document.data["quality_profiles"] if document.kind == "profiles" else [document.data]
        index = profiles if document.kind == "profiles" else formats
        label = "profile" if document.kind == "profiles" else "custom format"
        for obj in objects:
            key = (document.source, obj["name"])
            if key in index:
                raise ValueError(f"duplicate {label} {obj['name']!r}: {index[key]} and {document.path}")
            index[key] = document.path

    if not profiles:
        raise ValueError("catalog contains no profiles")

    for document in documents:
        if document.kind != "profiles":
            continue
        for profile in document.data["quality_profiles"]:
            prefix = f"{document.path}: profile {profile['name']!r}"
            if document.source == "sonarr" and "language" in profile:
                raise ValueError(f"{prefix}: language is only supported for Radarr")
            for name in profile["custom_format_scores"]:
                if (document.source, name) not in formats:
                    raise ValueError(f"{prefix}: unknown custom format {name!r}")
            names: set[str] = set()
            labels: set[str] = set()
            enabled: set[str] = set()
            for quality in profile["qualities"]:
                if quality["name"] in labels:
                    raise ValueError(f"{prefix}: duplicate quality {quality['name']!r}")
                labels.add(quality["name"])
                for name in quality.get("qualities", [quality["name"]]):
                    if name in names:
                        raise ValueError(f"{prefix}: duplicate quality {name!r}")
                    names.add(name)
                if quality.get("enabled", True):
                    enabled.add(quality["name"])
            cutoff = profile["upgrade"]["until_quality"]
            if cutoff not in enabled:
                raise ValueError(f"{prefix}: cutoff {cutoff!r} is not an enabled quality or group")
