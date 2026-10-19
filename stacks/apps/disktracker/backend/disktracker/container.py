"""The composition root: the database, every repository and service the API runs with, made by
providers and handed to whatever depends on them. The routes are wired to the services, which
are given their repositories; the repositories are given the database's session factories."""

from datetime import UTC, datetime
from uuid import uuid4

from dependency_injector import containers, providers

from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.repository import CatalogRepository
from disktracker.catalog.service import CatalogService
from disktracker.collection.client import CollectorClient
from disktracker.collection.repository import CollectionRepository
from disktracker.collection.service import CollectionService
from disktracker.database import Database
from disktracker.reporting.repository import ReportingRepository
from disktracker.reporting.service import ReportingService


def now() -> datetime:
    return datetime.now(UTC)


class Container(containers.DeclarativeContainer):
    # Wired by create_app. The route modules are shared by the process, so the routes serve the
    # application made last; a process serves one.
    wiring_config = containers.WiringConfiguration(
        modules=[
            "disktracker.catalog.routes",
            "disktracker.collection.routes",
            "disktracker.reporting.routes",
        ],
        auto_wire=False,
    )

    # database_url; collector_url, where the collector's API is (None: no collector to ask);
    # static_dir, the built frontend to serve (None: the API alone). Read by create_app.
    config = providers.Configuration()
    clock = providers.Object(now)
    next_id = providers.Object(uuid4)

    # One for the application: the engine, its pool and the session factories. Repositories and
    # services are made for each request and hold no session.
    # Disposed as the application stops; thread safe, as synchronous routes run on several
    # threads.
    database = providers.ThreadSafeSingleton(Database, url=config.database_url)

    catalog_repository = providers.Factory(
        CatalogRepository, session_factory=database.provided.session, now=clock, next_id=next_id
    )
    drive_repository = providers.Factory(DriveRepository, next_id=next_id)
    catalog_queries = providers.Factory(CatalogQueries, snapshot_factory=database.provided.snapshot)
    collection_repository = providers.Factory(
        CollectionRepository,
        session_factory=database.provided.session,
        snapshot_factory=database.provided.snapshot,
    )
    reporting_repository = providers.Factory(
        ReportingRepository,
        session_factory=database.provided.session,
        snapshot_factory=database.provided.snapshot,
    )

    collector_client = providers.Singleton(CollectorClient, url=config.collector_url)

    catalog_service = providers.Factory(
        CatalogService,
        repository=catalog_repository,
        queries=catalog_queries,
        now=clock,
        session_factory=database.provided.session,
        drives=drive_repository,
    )
    collection_service = providers.Factory(
        CollectionService,
        repository=collection_repository,
        catalog=catalog_queries,
        collector=collector_client,
        now=clock,
        next_id=next_id,
    )
    reporting_service = providers.Factory(
        ReportingService, repository=reporting_repository, now=clock
    )
