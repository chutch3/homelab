from dependency_injector import containers, providers

from backend.db.database import Database
from backend.repositories import JobRepository, ChunkRepository
from backend.services import JobService, ChunkService, TaskService


class ManagerContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    wiring_config = containers.WiringConfiguration(modules=[".endpoints"])

    database = providers.Singleton(
        Database,
        url=config.db.url,
    )

    job_repository = providers.Singleton(
        JobRepository,
        session_factory=database.provided.session,
    )

    chunk_repository = providers.Singleton(
        ChunkRepository,
        session_factory=database.provided.session,
    )

    job_service = providers.Factory(
        JobService,
        job_repo=job_repository,
        chunk_repo=chunk_repository,
    )

    chunk_service = providers.Factory(
        ChunkService,
        job_repo=job_repository,
        chunk_repo=chunk_repository,
    )

    task_service = providers.Factory(
        TaskService,
        job_repo=job_repository,
        chunk_repo=chunk_repository,
    )
