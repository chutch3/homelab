"""The composition root: the database, every repository and service the API runs with, made by
providers and handed to whatever depends on them. The routes are wired to the services, which
are given their repositories; the repositories are given the database's session factories."""

from datetime import UTC, datetime
from uuid import uuid4

from dependency_injector import containers, providers

from disktracker.catalog.condition_rule_repository import ConditionRuleRepository
from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.drive_service import DriveService
from disktracker.catalog.ingestion_service import IngestionService
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.offer_service import OfferService
from disktracker.catalog.price_service import PriceService
from disktracker.catalog.queries import CatalogQueries
from disktracker.catalog.review_repository import ReviewRepository
from disktracker.catalog.review_service import ReviewService
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

    drive_repository = providers.Factory(DriveRepository, next_id=next_id)
    offer_repository = providers.Factory(OfferRepository, now=clock, next_id=next_id)
    review_repository = providers.Factory(ReviewRepository, next_id=next_id)
    condition_rule_repository = providers.Factory(ConditionRuleRepository)
    catalog_queries = providers.Factory(
        CatalogQueries, snapshot_factory=database.provided.snapshot, offers=offer_repository
    )
    collection_repository = providers.Factory(
        CollectionRepository,
        session_factory=database.provided.session,
        snapshot_factory=database.provided.snapshot,
    )
    reporting_repository = providers.Factory(
        ReportingRepository,
        session_factory=database.provided.session,
        snapshot_factory=database.provided.snapshot,
        offers=offer_repository,
    )

    collector_client = providers.Singleton(CollectorClient, url=config.collector_url)

    price_service = providers.Factory(
        PriceService,
        session_factory=database.provided.session,
        drives=drive_repository,
        offers=offer_repository,
    )
    ingestion_service = providers.Factory(
        IngestionService,
        session_factory=database.provided.session,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
        now=clock,
    )
    review_service = providers.Factory(
        ReviewService,
        session_factory=database.provided.session,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
    )
    drive_service = providers.Factory(
        DriveService,
        session_factory=database.provided.session,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
    )
    offer_service = providers.Factory(
        OfferService, session_factory=database.provided.session, offers=offer_repository
    )
    condition_rule_service = providers.Factory(
        ConditionRuleService,
        session_factory=database.provided.session,
        rules=condition_rule_repository,
    )
    catalog_service = providers.Factory(CatalogService, queries=catalog_queries, now=clock)
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
