from __future__ import annotations

from typing import Any

from fiber.clients.discovery import LazyDockerGateway


def extract_services(raw_services: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for svc in raw_services:
        spec = svc.get("Spec", {})
        name = spec.get("Name")
        if name:
            out[name] = dict(spec.get("Labels") or {})
    return out


def extract_image(raw_service: dict[str, Any]) -> tuple[str | None, str | None]:
    image = (
        raw_service.get("Spec", {}).get("TaskTemplate", {})
        .get("ContainerSpec", {}).get("Image")
    )
    if not image:
        return None, None
    tag, _, digest = image.partition("@")
    return tag, (digest or None)


class DockerSwarmGateway(LazyDockerGateway):
    def list_dump_services(self) -> dict[str, dict[str, str]]:
        client = self._get_client()
        raw = [s.attrs for s in client.services.list()]
        return extract_services(raw)

    def image_of(self, service: str) -> tuple[str | None, str | None]:
        client = self._get_client()
        svc = client.services.get(service)
        return extract_image(svc.attrs)
