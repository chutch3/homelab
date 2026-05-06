import asyncio

from worker.containers import WorkerContainer
from worker.daemon import run_daemon


async def main():
    container = WorkerContainer()
    container.config.manager_url.from_env("MANAGER_URL", "http://takeout-manager:8000")
    container.config.log.level.from_env("LOG_LEVEL", "INFO")
    container.config.paths.downloads.from_env("DOWNLOAD_PATH", "/downloads")
    container.config.paths.pictures.from_env("PICTURES_PATH", "/pictures")
    container.config.paths.videos.from_env("VIDEOS_PATH", "/videos")

    await container.init_resources()

    try:
        await run_daemon()
    finally:
        await container.shutdown_resources()


if __name__ == "__main__":
    asyncio.run(main())
