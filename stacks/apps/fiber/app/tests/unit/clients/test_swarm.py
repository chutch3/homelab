from __future__ import annotations

from unittest.mock import MagicMock, create_autospec

import docker
import pytest

from fiber.clients.swarm import DockerSwarmGateway, extract_image, extract_services


# ---------------------------------------------------------------------------
# Pure-function tests — stay flat
# ---------------------------------------------------------------------------

def test_extract_services_returns_name_to_labels() -> None:
    raw = [
        {"Spec": {"Name": "kenku-pg", "Labels": {"fiber.enable": "true", "fiber.dbname": "k"}}},
        {"Spec": {"Name": "other", "Labels": {}}},
    ]
    assert extract_services(raw) == {
        "kenku-pg": {"fiber.enable": "true", "fiber.dbname": "k"},
        "other": {},
    }


def test_extract_image_returns_tag_and_digest() -> None:
    spec = {"Spec": {"TaskTemplate": {"ContainerSpec": {
        "Image": "ghcr.io/chutch3/kenku:0.28.1@sha256:deadbeef"}}}}
    assert extract_image(spec) == ("ghcr.io/chutch3/kenku:0.28.1", "sha256:deadbeef")


# ---------------------------------------------------------------------------
# DockerSwarmGateway class tests
# ---------------------------------------------------------------------------

class TestDockerSwarmGateway:
    @pytest.fixture()
    def docker_client(self) -> MagicMock:
        return create_autospec(docker.DockerClient, instance=True)

    @pytest.fixture()
    def subject(self, docker_client: MagicMock) -> DockerSwarmGateway:
        return DockerSwarmGateway(client_factory=lambda: docker_client)

    def test_list_dump_services_calls_services_list_and_maps(
        self, subject: DockerSwarmGateway, docker_client: MagicMock
    ) -> None:
        fake_svc = MagicMock()
        fake_svc.attrs = {
            "Spec": {
                "Name": "kenku-pg",
                "Labels": {"fiber.enable": "true"},
            }
        }
        docker_client.services.list.return_value = [fake_svc]
        result = subject.list_dump_services()
        docker_client.services.list.assert_called_once()
        assert result == {"kenku-pg": {"fiber.enable": "true"}}

    def test_image_of_calls_services_get(
        self, subject: DockerSwarmGateway, docker_client: MagicMock
    ) -> None:
        fake_svc = MagicMock()
        fake_svc.attrs = {"Spec": {"TaskTemplate": {"ContainerSpec": {
            "Image": "img:1@sha256:abc"
        }}}}
        docker_client.services.get.return_value = fake_svc
        tag, digest = subject.image_of("kenku-pg")
        docker_client.services.get.assert_called_once_with("kenku-pg")
        assert tag == "img:1"
        assert digest == "sha256:abc"

    def test_construction_with_raising_factory_does_not_raise(self) -> None:
        """The gateway must be constructable even when the factory would raise."""
        def bad_factory() -> docker.DockerClient:
            raise docker.errors.DockerException("no socket")

        # Must NOT raise at construction time
        gateway = DockerSwarmGateway(client_factory=bad_factory)
        assert gateway is not None

    def test_list_dump_services_raises_when_factory_raises(self) -> None:
        """list_dump_services() propagates factory errors (lazy client creation)."""
        def bad_factory() -> docker.DockerClient:
            raise docker.errors.DockerException("no socket")

        gateway = DockerSwarmGateway(client_factory=bad_factory)
        with pytest.raises(docker.errors.DockerException, match="no socket"):
            gateway.list_dump_services()

    def test_client_is_created_lazily_on_first_call(self, docker_client: MagicMock) -> None:
        """The factory is not called until the first I/O method is invoked."""
        call_count = 0

        def counting_factory() -> MagicMock:
            nonlocal call_count
            call_count += 1
            return docker_client

        docker_client.services.list.return_value = []
        gateway = DockerSwarmGateway(client_factory=counting_factory)
        assert call_count == 0, "factory called at construction time (must be lazy)"
        gateway.list_dump_services()
        assert call_count == 1

    def test_client_is_cached_across_calls(self, docker_client: MagicMock) -> None:
        """The factory is called exactly once, even across multiple I/O calls."""
        call_count = 0

        def counting_factory() -> MagicMock:
            nonlocal call_count
            call_count += 1
            return docker_client

        docker_client.services.list.return_value = []
        fake_svc = MagicMock()
        fake_svc.attrs = {"Spec": {"TaskTemplate": {"ContainerSpec": {"Image": "img:1"}}}}
        docker_client.services.get.return_value = fake_svc

        gateway = DockerSwarmGateway(client_factory=counting_factory)
        gateway.list_dump_services()
        gateway.image_of("kenku-pg")
        assert call_count == 1, "factory called more than once (must be cached)"
