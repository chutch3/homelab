from __future__ import annotations

from typing import Any, Callable


class DockerContainerGateway:
    """Discovery via the standalone Docker API: lists containers, reads container labels."""

    def __init__(self, client_factory: Callable[[], Any]) -> None:
        self._client_factory = client_factory
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def list_dump_services(self) -> dict[str, dict[str, str]]:
        client = self._get_client()
        containers = client.containers.list(filters={"label": "fiber.enable=true"})
        return {c.name: dict(c.labels or {}) for c in containers}

    def image_of(self, name: str) -> tuple[str | None, str | None]:
        client = self._get_client()
        container = client.containers.get(name)
        tags = container.image.tags
        return (tags[0] if tags else None, None)
