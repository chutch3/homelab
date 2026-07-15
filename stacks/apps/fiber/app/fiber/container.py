from __future__ import annotations

import docker
from dependency_injector import containers, providers
from fastapi.templating import Jinja2Templates
from prometheus_client import CollectorRegistry

import fiber
from fiber.clients.bowl import BowlStorage
from fiber.clients.events import EventBroker
from fiber.platform.clock import SystemClock
from fiber.platform.config import Config
from fiber.db.database import Database
from fiber.clients.dump_runner import DumpRunner
from fiber.clients.engines import build_default_engines
from fiber.clients.probe import ConnectivityProbe
from fiber.repositories.history import HistoryRepository
from fiber.platform.metrics import Metrics
from fiber.services.dashboard import DashboardService
from fiber.services.orchestrator import MovementOrchestrator
from fiber.services.readiness import Readiness
from fiber.services.registry_state import RegistryState
from fiber.clients.secrets import SecretReader
from fiber.clients.container import DockerContainerGateway
from fiber.clients.swarm import DockerSwarmGateway
from fiber.services.worker_pool import WorkerPool


class Container(containers.DeclarativeContainer):
    config = providers.Singleton(Config.from_env)
    registry = providers.Singleton(CollectorRegistry)
    metrics = providers.Singleton(Metrics, registry=registry)
    clock = providers.Singleton(SystemClock)
    bowl = providers.Singleton(BowlStorage, root=config.provided.bowl_path)
    database = providers.Singleton(Database, url=config.provided.db_url)
    history_repository = providers.Singleton(HistoryRepository, session_factory=database.provided.session)
    secrets = providers.Singleton(SecretReader, base_dir=config.provided.secrets_dir)
    engines = providers.Singleton(build_default_engines)
    runner = providers.Singleton(DumpRunner, engines=engines)
    probe = providers.Singleton(ConnectivityProbe, engines=engines)
    docker_client = providers.Factory(docker.DockerClient, base_url=config.provided.docker_host)
    swarm_gateway = providers.Singleton(DockerSwarmGateway, client_factory=docker_client.provider)
    container_gateway = providers.Singleton(DockerContainerGateway, client_factory=docker_client.provider)
    active_provider = providers.Callable(lambda c: c.provider, config)
    discovery = providers.Selector(
        active_provider,
        swarm=swarm_gateway,
        docker=container_gateway,
    )
    pool = providers.Singleton(WorkerPool, max_concurrent=config.provided.max_concurrent)
    bowl_factory = providers.Factory(BowlStorage)
    events = providers.Singleton(EventBroker)
    registry_state = providers.Singleton(RegistryState)
    orchestrator = providers.Singleton(
        MovementOrchestrator, bowl_factory=bowl_factory.provider, bowl_root=config.provided.bowl_path,
        secrets=secrets, runner=runner,
        history=history_repository, discovery=discovery, clock=clock, fiber_version=fiber.__version__,
        metrics=metrics, events=events,
    )
    readiness = providers.Singleton(Readiness, bowl=bowl, history=history_repository, discovery=discovery)
    templates = providers.Singleton(Jinja2Templates, directory="fiber/templates")
    dashboard_service = providers.Singleton(
        DashboardService,
        registry_state=registry_state,
        history=history_repository,
        pool=pool,
        bowl=bowl,
        now=clock.provided.now,
        default_bowl_root=config.provided.bowl_path,
    )
