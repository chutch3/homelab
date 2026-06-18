from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class DiscoveryProvider(Protocol):
    """Owned seam over Docker discovery — implemented by the swarm and container gateways."""

    def list_dump_services(self) -> dict[str, dict[str, str]]: ...

    def image_of(self, name: str) -> tuple[str | None, str | None]: ...
