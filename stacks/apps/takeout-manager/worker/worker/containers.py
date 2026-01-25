import logging
import sys

from dependency_injector import containers, providers

from worker.logger import StructuredFormatter
from worker.manager_client import ManagerClient, init_async_client
from worker.runners import CurlRunner, TarRunner
from worker.services import DownloadService


def configure_logging(level: str = "INFO"):
    """Configure structured logging for the worker."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)

    yield

    # Cleanup on shutdown
    root_logger.removeHandler(handler)
    handler.close()


class WorkerContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    wiring_config = containers.WiringConfiguration(
        modules=["worker.daemon"], warn_unresolved=True
    )
    logging = providers.Resource(
        configure_logging,
        level=config.log.level,
    )

    async_client = providers.Resource(init_async_client, manager_url=config.manager_url)

    manager_client = providers.Singleton(ManagerClient, client=async_client)

    curl_runner = providers.Singleton(
        CurlRunner,
    )

    tar_runner = providers.Singleton(
        TarRunner,
    )

    download_service = providers.Factory(
        DownloadService,
        curl_runner=curl_runner,
        tar_runner=tar_runner,
    )
