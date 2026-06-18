from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import docker
import pytest

from fiber.clients.container import DockerContainerGateway


class TestDockerContainerGateway:
    @pytest.fixture()
    def docker_client(self) -> MagicMock:
        return create_autospec(docker.DockerClient, instance=True)

    @pytest.fixture()
    def subject(self, docker_client: MagicMock) -> DockerContainerGateway:
        return DockerContainerGateway(client_factory=lambda: docker_client)

    def test_list_dump_services_filters_and_maps(self, subject, docker_client) -> None:
        fake = MagicMock()
        fake.name = "e2e-pg"                       # set after construction (MagicMock(name=) is special)
        fake.labels = {"fiber.enable": "true", "fiber.provider": "docker"}
        docker_client.containers.list.return_value = [fake]

        result = subject.list_dump_services()

        docker_client.containers.list.assert_called_once_with(filters={"label": "fiber.enable=true"})
        assert result == {"e2e-pg": {"fiber.enable": "true", "fiber.provider": "docker"}}

    def test_image_of_returns_first_tag(self, subject, docker_client) -> None:
        fake = MagicMock()
        fake.image.tags = ["ghcr.io/chutch3/app:1.2.3"]
        docker_client.containers.get.return_value = fake
        tag, digest = subject.image_of("e2e-pg")
        docker_client.containers.get.assert_called_once_with("e2e-pg")
        assert tag == "ghcr.io/chutch3/app:1.2.3"
        assert digest is None

    def test_construction_with_raising_factory_does_not_raise(self) -> None:
        def bad_factory() -> docker.DockerClient:
            raise docker.errors.DockerException("no socket")
        assert DockerContainerGateway(client_factory=bad_factory) is not None

    def test_client_created_lazily_and_cached(self, docker_client) -> None:
        calls = 0
        def factory() -> MagicMock:
            nonlocal calls
            calls += 1
            return docker_client
        docker_client.containers.list.return_value = []
        gw = DockerContainerGateway(client_factory=factory)
        assert calls == 0
        gw.list_dump_services()
        gw.list_dump_services()
        assert calls == 1
