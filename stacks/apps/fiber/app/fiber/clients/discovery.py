from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable


@runtime_checkable
class DiscoveryProvider(Protocol):
    """Owned seam over Docker discovery — implemented by the swarm and container gateways."""

    def list_dump_services(self) -> dict[str, dict[str, str]]: ...

    def image_of(self, name: str) -> tuple[str | None, str | None]: ...


class LazyDockerGateway:
    """Shared lazy/cached Docker client wiring for the discovery gateways.

    The client is created on first use rather than at construction, so the
    container can wire a gateway even when no Docker socket is reachable
    (keeps ``/readyz`` graceful). Subclasses implement ``list_dump_services``
    and ``image_of`` against ``self._get_client()``.
    """

    def __init__(self, client_factory: Callable[[], Any]) -> None:
        self._client_factory = client_factory
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client
