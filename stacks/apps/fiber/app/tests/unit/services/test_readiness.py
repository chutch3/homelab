from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from fiber.clients.bowl import BowlStorage
from fiber.repositories.history import HistoryRepository
from fiber.services.readiness import Readiness
from fiber.clients.swarm import DockerSwarmGateway


class TestReadiness:
    @pytest.fixture()
    def bowl(self) -> MagicMock:
        m = MagicMock(spec=BowlStorage)
        m.has_room.return_value = True
        return m

    @pytest.fixture()
    def history(self) -> MagicMock:
        m = MagicMock(spec=HistoryRepository)
        m.last_success.return_value = None
        return m

    @pytest.fixture()
    def swarm(self) -> MagicMock:
        m = MagicMock(spec=DockerSwarmGateway)
        m.list_dump_services.return_value = {}
        return m

    @pytest.fixture()
    def subject(self, bowl: MagicMock, history: MagicMock, swarm: MagicMock) -> Readiness:
        return Readiness(bowl=bowl, history=history, discovery=swarm)

    def test_readiness_true_when_all_ok(self, subject: Readiness, bowl: MagicMock) -> None:
        assert subject() is True
        bowl.has_room.assert_called_once_with(1)

    def test_readiness_false_when_swarm_raises(
        self, subject: Readiness, swarm: MagicMock
    ) -> None:
        swarm.list_dump_services.side_effect = RuntimeError("docker down")
        assert subject() is False

    def test_readiness_false_when_bowl_full(
        self, subject: Readiness, bowl: MagicMock
    ) -> None:
        bowl.has_room.return_value = False
        assert subject() is False

    def test_readiness_false_when_history_raises(
        self, subject: Readiness, history: MagicMock
    ) -> None:
        history.last_success.side_effect = Exception("db locked")
        assert subject() is False

    def test_readiness_false_when_swarm_raises_docker_exception(
        self, subject: Readiness, swarm: MagicMock
    ) -> None:
        import docker
        swarm.list_dump_services.side_effect = docker.errors.DockerException("gateway unreachable")
        assert subject() is False

    def test_readiness_never_raises_even_when_all_checks_fail(
        self, bowl: MagicMock, history: MagicMock, swarm: MagicMock
    ) -> None:
        """__call__ must never propagate exceptions — route depends on False, not 500."""
        bowl.has_room.side_effect = RuntimeError("bowl exploded")
        history.last_success.side_effect = RuntimeError("db exploded")
        swarm.list_dump_services.side_effect = RuntimeError("swarm exploded")
        subject = Readiness(bowl=bowl, history=history, discovery=swarm)
        # Must return False, not raise
        result = subject()
        assert result is False

    def test_readiness_false_when_swarm_factory_raises_on_call(
        self, bowl: MagicMock, history: MagicMock
    ) -> None:
        """Real DockerSwarmGateway with a raising factory: __call__ returns False not 500."""
        import docker
        from fiber.clients.swarm import DockerSwarmGateway

        def bad_factory() -> docker.DockerClient:
            raise docker.errors.DockerException("no docker socket")

        real_swarm = DockerSwarmGateway(client_factory=bad_factory)
        subject = Readiness(bowl=bowl, history=history, discovery=real_swarm)
        assert subject() is False
