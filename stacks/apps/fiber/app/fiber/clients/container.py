from __future__ import annotations

from typing import Any

from fiber.clients.discovery import LazyDockerGateway


def extract_containers(containers: list[Any]) -> dict[str, dict[str, str]]:
    """Map discovered containers to ``{name: labels}`` (pure; no I/O)."""
    return {c.name: dict(c.labels or {}) for c in containers}


def extract_container_image(container: Any) -> tuple[str | None, str | None]:
    """Return ``(first tag, digest)`` for a container's image, mirroring the
    swarm gateway's ``extract_image``. Digest comes from ``RepoDigests``."""
    image = container.image
    tags = image.tags
    repo_digests = (image.attrs or {}).get("RepoDigests") or []
    digest = next((rd.split("@", 1)[1] for rd in repo_digests if "@" in rd), None)
    return (tags[0] if tags else None, digest)


class DockerContainerGateway(LazyDockerGateway):
    """Discovery via the standalone Docker API: lists containers, reads container labels."""

    def list_dump_services(self) -> dict[str, dict[str, str]]:
        client = self._get_client()
        containers = client.containers.list(filters={"label": "fiber.enable=true"})
        return extract_containers(containers)

    def image_of(self, name: str) -> tuple[str | None, str | None]:
        client = self._get_client()
        return extract_container_image(client.containers.get(name))
