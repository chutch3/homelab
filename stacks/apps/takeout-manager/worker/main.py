import asyncio

from worker.containers import WorkerContainer
from worker.daemon import run_daemon


async def main():
    # Configure Dependency Injector Container
    container = WorkerContainer()
    container.config.manager_url.from_env("MANAGER_URL", "http://takeout-manager:8000")
    container.config.log.level.from_env("LOG_LEVEL", "INFO")

    # Initialize resources (logging, async client)
    await container.init_resources()

    try:
        # Run the daemon
        await run_daemon()
    finally:
        # Shutdown resources
        await container.shutdown_resources()


if __name__ == "__main__":
    asyncio.run(main())
