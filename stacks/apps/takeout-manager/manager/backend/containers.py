from dependency_injector import containers, providers

from backend.db import Database
from backend.repositories import JobRepository, ChunkRepository
from backend.services import JobService, ChunkService, TaskService


class ManagerContainer(containers.DeclarativeContainer):
    config = providers.Configuration()

    wiring_config = containers.WiringConfiguration(modules=[".endpoints"])

    # Database
    database = providers.Singleton(
        Database,
        db_path=config.db.path,
    )

    # Repositories
    job_repository = providers.Factory(
        JobRepository,
        db=database,
    )

    chunk_repository = providers.Factory(
        ChunkRepository,
        db=database,
    )

    # Services
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
