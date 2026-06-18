from fiber.clients.container import DockerContainerGateway
from fiber.clients.discovery import DiscoveryProvider
from fiber.clients.swarm import DockerSwarmGateway


def test_both_gateways_satisfy_discovery_protocol() -> None:
    assert isinstance(DockerSwarmGateway(client_factory=lambda: None), DiscoveryProvider)
    assert isinstance(DockerContainerGateway(client_factory=lambda: None), DiscoveryProvider)
