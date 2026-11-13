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
from disktracker.collector.run_repository import RunRepository
from disktracker.collector.run_service import RunService
from disktracker.collector.source_repository import SourceRepository
from disktracker.collector.source_service import SourceService
from disktracker.database import Database, Transactions
from disktracker.reporting.reporting_repository import ReportingRepository
from disktracker.reporting.reporting_service import ReportingService


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
    # One of each for the application: none keeps anything of a request, the transaction each
    # thread is in being the session registry's. Thread safe, as synchronous routes run on
    # several threads.
    clock = providers.ThreadSafeSingleton(Clock)

    # The engine and its pool, disposed as the application stops.
    database = providers.ThreadSafeSingleton(Database, url=config.database_url)
    sessions = database.provided.sessions
    transactions = providers.ThreadSafeSingleton(Transactions, sessions=sessions)

    drive_repository = providers.ThreadSafeSingleton(DriveRepository, session=sessions)
    offer_repository = providers.ThreadSafeSingleton(OfferRepository, session=sessions, clock=clock)
    review_repository = providers.ThreadSafeSingleton(ReviewRepository, session=sessions)
    condition_rule_repository = providers.ThreadSafeSingleton(
        ConditionRuleRepository, session=sessions
    )
    source_repository = providers.ThreadSafeSingleton(SourceRepository, session=sessions)
    run_repository = providers.ThreadSafeSingleton(RunRepository, session=sessions)
    reporting_repository = providers.ThreadSafeSingleton(
        ReportingRepository,
        session=sessions,
        offers=offer_repository,
        drives=drive_repository,
    )

    collector_client = providers.ThreadSafeSingleton(CollectorClient, url=config.collector_url)

    price_service = providers.ThreadSafeSingleton(
        PriceService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
    )
    ingestion_service = providers.ThreadSafeSingleton(
        IngestionService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
        clock=clock,
    )
    review_service = providers.ThreadSafeSingleton(
        ReviewService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
    )
    drive_service = providers.ThreadSafeSingleton(
        DriveService,
        transactions=transactions,
        drives=drive_repository,
        offers=offer_repository,
        reviews=review_repository,
    )
    offer_service = providers.ThreadSafeSingleton(
        OfferService,
        transactions=transactions,
        offers=offer_repository,
    )
    condition_rule_service = providers.ThreadSafeSingleton(
        ConditionRuleService,
        transactions=transactions,
        rules=condition_rule_repository,
    )
    source_service = providers.ThreadSafeSingleton(
        SourceService,
        transactions=transactions,
        sources=source_repository,
        clock=clock,
    )
    run_service = providers.ThreadSafeSingleton(
        RunService,
        transactions=transactions,
        runs=run_repository,
        sources=source_repository,
        clock=clock,
    )
    preview_service = providers.ThreadSafeSingleton(
        PreviewService,
        rules=condition_rule_service,
        ingestion=ingestion_service,
        collector=collector_client,
    )
    reporting_service = providers.ThreadSafeSingleton(
        ReportingService, transactions=transactions, repository=reporting_repository, clock=clock
    )
