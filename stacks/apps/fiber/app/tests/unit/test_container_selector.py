from fiber.clients.container import DockerContainerGateway
from fiber.clients.swarm import DockerSwarmGateway
from fiber.container import Container


def test_selector_defaults_to_swarm(monkeypatch) -> None:
    monkeypatch.delenv("FIBER_PROVIDER", raising=False)
    assert isinstance(Container().discovery(), DockerSwarmGateway)


def test_selector_picks_docker(monkeypatch) -> None:
    monkeypatch.setenv("FIBER_PROVIDER", "docker")
    assert isinstance(Container().discovery(), DockerContainerGateway)
