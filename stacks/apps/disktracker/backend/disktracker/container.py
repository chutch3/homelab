"""The composition root: the database, every repository and service the API runs with, made by
providers and handed to whatever depends on them. The routes are wired to the services, which
are given their repositories and the transactions their methods run in."""

from dependency_injector import containers, providers

from disktracker.catalog.condition_rule_repository import ConditionRuleRepository
from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.drive_repository import DriveRepository
from disktracker.catalog.drive_service import DriveService
from disktracker.catalog.ingestion_service import IngestionService
from disktracker.catalog.offer_repository import OfferRepository
from disktracker.catalog.offer_service import OfferService
from disktracker.catalog.price_service import PriceService
from disktracker.catalog.review_repository import ReviewRepository
from disktracker.catalog.review_service import ReviewService
from disktracker.clock import Clock
from disktracker.collector.client import CollectorClient
from disktracker.collector.preview_service import PreviewService
from disktracker.collector.repository import CollectionRepository
from disktracker.collector.service import CollectionService
from disktracker.database import Database, Transactions
from disktracker.reporting.repository import ReportingRepository
from disktracker.reporting.service import ReportingService


class Container(containers.DeclarativeContainer):
    # Wired by create_app. The route modules are shared by the process, so the routes serve the
    # application made last; a process serves one.
    wiring_config = containers.WiringConfiguration(
        modules=[
            "disktracker.catalog.routes",
            "disktracker.collector.routes",
            "disktracker.reporting.routes",
        ],
        auto_wire=False,
    )

    # database_url; collector_url, where the collector's API is (None: no collector to ask);
    # static_dir, the built frontend to serve (None: the API alone). Read by create_app.
    config = providers.Configuration()
    clock = providers.Singleton(Clock)

    # One for the application: the engine and its pool. Disposed as the application stops;
    # thread safe, as synchronous routes run on several threads.
    database = providers.ThreadSafeSingleton(Database, url=config.database_url)
    transactions = providers.Factory(Transactions, database=database)

    drive_repository = providers.Factory(DriveRepository)
    offer_repository = providers.Factory(OfferRepository, clock=clock)
    review_repository = providers.Factory(ReviewRepository)
    condition_rule_repository = providers.Factory(ConditionRuleRepository)
    collection_repository = providers.Factory(CollectionRepository)
    reporting_repository = providers.Factory(
        ReportingRepository,
        offers=offer_repository,
        drives=drive_repository,
    )

    collector_client = providers.Singleton(CollectorClient, url=config.collector_url)

    price_service = providers.Factory(
        PriceService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
    )
    ingestion_service = providers.Factory(
        IngestionService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
        clock=clock,
    )
    review_service = providers.Factory(
        ReviewService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
    )
    drive_service = providers.Factory(
        DriveService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
    )
    offer_service = providers.Factory(
        OfferService,
        transactions=transactions,
        offers=offer_repository,
    )
    condition_rule_service = providers.Factory(
        ConditionRuleService,
        transactions=transactions,
        rules=condition_rule_repository,
    )
    collection_service = providers.Factory(
        CollectionService,
        transactions=transactions,
        repository=collection_repository,
        clock=clock,
    )
    preview_service = providers.Factory(
        PreviewService,
        rules=condition_rule_service,
        ingestion=ingestion_service,
        collector=collector_client,
    )
    reporting_service = providers.Factory(
        ReportingService, transactions=transactions, repository=reporting_repository, clock=clock
    )
