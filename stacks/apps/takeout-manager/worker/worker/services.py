import asyncio
import logging
import os
import shutil
import tempfile
from typing import Any, Awaitable, Callable, Optional

from worker.runners import CurlRunner, GpthRunner, TarRunner
from worker.progress import DownloadProgressTracker

PICTURE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}

ProgressCallback = Callable[[int, Optional[int], float], Awaitable[None]]


class DownloadService:
    def __init__(
        self,
        curl_runner: CurlRunner,
        tar_runner: TarRunner,
        progress_tracker: DownloadProgressTracker,
        staging_path: str,
        download_path: str,
        pictures_path: str,
        videos_path: str,
    ) -> None:
        self.curl_runner = curl_runner
        self.tar_runner = tar_runner
        self.progress_tracker = progress_tracker
        self.staging_path = staging_path
        self.download_path = download_path
        self.pictures_path = pictures_path
        self.videos_path = videos_path
        self.logger = logging.getLogger(self.__class__.__name__)

    async def download_chunk(
        self, task: dict[str, Any], on_progress: Optional[ProgressCallback] = None
    ) -> tuple[bool, str]:
        params = task.get("params", {})
        chunk_index = params.get("chunk_index")
        timestamp = params.get("timestamp")
        job_id = params.get("job_id")
        user_id = params.get("user_id")
        auth_user = params.get("auth_user")
        cookie = params.get("cookie")

        if any(v is None for v in [chunk_index, timestamp, job_id, user_id, auth_user, cookie]):
            return False, "Missing required download parameters"

        chunk_num_str = f"{chunk_index:03d}"

        output_file = f"takeout-{timestamp}Z-1-{chunk_num_str}.tgz"
        staging_file_path = os.path.join(self.staging_path, output_file)
        output_path = os.path.join(self.download_path, output_file)
        url = (
            f"https://takeout-download.usercontent.google.com/download/{output_file}"
            f"?j={job_id}&i={chunk_index - 1}&user={user_id}&authuser={auth_user}"
        )

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.6",
            "priority": "u=0, i",
            "referer": "https://takeout.google.com/",
            "sec-ch-ua": '"Not=A?Brand";v="99", "Brave";v="151", "Chromium";v="151"',
            "sec-ch-ua-arch": '"x86"',
            "sec-ch-ua-bitness": '"64"',
            "sec-ch-ua-full-version-list": '"Not=A?Brand";v="99.0.0.0", "Brave";v="151.0.0.0", "Chromium";v="151.0.0.0"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-model": '""',
            "sec-ch-ua-platform": '"Linux"',
            "sec-ch-ua-platform-version": '""',
            "sec-ch-ua-wow64": "?0",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-site",
            "sec-gpc": "1",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
            "cookie": cookie,
        }

        total_bytes = await self.curl_runner.probe_total_size(url, headers)

        tracker_task = None
        stop_event = asyncio.Event()
        if on_progress is not None:
            tracker_task = asyncio.create_task(
                self.progress_tracker.track(staging_file_path, total_bytes, on_progress, stop_event)
            )

        try:
            success = await self.curl_runner.download(url, staging_file_path, headers)
        finally:
            if tracker_task is not None:
                stop_event.set()
                await tracker_task

        if success and os.path.exists(staging_file_path) and os.path.getsize(staging_file_path) > 0:
            if not await self.tar_runner.verify(staging_file_path):
                os.remove(staging_file_path)
                return False, "Downloaded file failed integrity check (corrupted)"
            os.makedirs(self.download_path, exist_ok=True)
            shutil.move(staging_file_path, output_path)
            return True, "Download successful"
        elif success:
            return False, "File not found or empty after download"
        else:
            return False, "Download failed"

    async def extract_chunk(self, task: dict[str, Any]) -> tuple[bool, str]:
        params = task.get("params", {})
        if not params:
            return False, "Task parameters are missing"

        timestamp = params.get("timestamp")
        chunk_index = params.get("chunk_index")

        if not all([timestamp, chunk_index]):
            return False, "Missing required parameters for extraction (timestamp, chunk_index)"

        chunk_num_str = f"{chunk_index:03d}"
        output_file = f"takeout-{timestamp}Z-1-{chunk_num_str}.tgz"
        tgz_path = os.path.join(self.download_path, output_file)

        if not os.path.exists(tgz_path):
            return False, f"Archive not found: {tgz_path}"

        temp_extract_dir = tempfile.mkdtemp(prefix="extract_temp_")

        try:
            success = await self.tar_runner.extract(tgz_path, temp_extract_dir)
            if not success:
                return False, "Failed to extract archive"

            pictures_moved = 0
            videos_moved = 0

            for root, _, files in os.walk(temp_extract_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    _, ext = os.path.splitext(file)
                    ext_lower = ext.lower()

                    if ext_lower in PICTURE_EXTENSIONS:
                        os.makedirs(self.pictures_path, exist_ok=True)
                        shutil.move(file_path, os.path.join(self.pictures_path, file))
                        pictures_moved += 1
                    elif ext_lower in VIDEO_EXTENSIONS:
                        os.makedirs(self.videos_path, exist_ok=True)
                        shutil.move(file_path, os.path.join(self.videos_path, file))
                        videos_moved += 1

            return True, f"Extracted {pictures_moved} pictures and {videos_moved} videos"

        except Exception as e:
            self.logger.error("Extraction failed with exception: %s", e)
            return False, f"Extraction error: {str(e)}"

        finally:
            try:
                if os.path.exists(temp_extract_dir):
                    shutil.rmtree(temp_extract_dir)
            except Exception as cleanup_error:
                self.logger.warning("Failed to cleanup temp directory %s: %s", temp_extract_dir, cleanup_error)


class MetadataService:
    def __init__(
        self,
        tar_runner: TarRunner,
        gpth_runner: GpthRunner,
        download_path: str,
        pictures_path: str,
        videos_path: str,
    ) -> None:
        self.tar_runner = tar_runner
        self.gpth_runner = gpth_runner
        self.download_path = download_path
        self.pictures_path = pictures_path
        self.videos_path = videos_path
        self.logger = logging.getLogger(self.__class__.__name__)

    async def process_job_metadata(self, task: dict[str, Any]) -> tuple[bool, str]:
        params = task.get("params", {})
        job_id = params.get("job_id")
        timestamp = params.get("timestamp")
        total_chunks = params.get("total_chunks")

        if any(v is None for v in [job_id, timestamp, total_chunks]):
            return False, "Missing required metadata parameters"

        raw_dir = tempfile.mkdtemp(prefix="metadata_raw_")
        gpth_output_dir = tempfile.mkdtemp(prefix="metadata_gpth_")

        try:
            for chunk_index in range(1, total_chunks + 1):
                chunk_num_str = f"{chunk_index:03d}"
                archive_file = f"takeout-{timestamp}Z-1-{chunk_num_str}.tgz"
                archive_path = os.path.join(self.download_path, archive_file)

                if not os.path.exists(archive_path):
                    return False, f"Archive not found: {archive_path}"

                success = await self.tar_runner.extract(archive_path, raw_dir)
                if not success:
                    return False, f"Failed to re-extract chunk {chunk_index}"

            if not await self.gpth_runner.process(raw_dir, gpth_output_dir):
                return False, "GPTH processing failed"

            pictures_moved = 0
            videos_moved = 0

            for root, _, files in os.walk(gpth_output_dir):
                rel_dir = os.path.relpath(root, gpth_output_dir)
                for file in files:
                    _, ext = os.path.splitext(file)
                    ext_lower = ext.lower()

                    if ext_lower in PICTURE_EXTENSIONS:
                        dest_root = self.pictures_path
                        pictures_moved += 1
                    elif ext_lower in VIDEO_EXTENSIONS:
                        dest_root = self.videos_path
                        videos_moved += 1
                    else:
                        continue

                    dest_dir = os.path.join(dest_root, rel_dir) if rel_dir != "." else dest_root
                    os.makedirs(dest_dir, exist_ok=True)
                    dest_path = os.path.join(dest_dir, file)

                    flat_copy_path = os.path.join(dest_root, file)
                    if flat_copy_path != dest_path and os.path.exists(flat_copy_path):
                        os.remove(flat_copy_path)

                    shutil.move(os.path.join(root, file), dest_path)

            return True, f"Processed metadata for {pictures_moved} pictures and {videos_moved} videos"

        except Exception as e:
            self.logger.error("Metadata processing failed with exception: %s", e)
            return False, f"Metadata processing error: {str(e)}"

        finally:
            for temp_dir in (raw_dir, gpth_output_dir):
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                except Exception as cleanup_error:
                    self.logger.warning("Failed to cleanup temp directory %s: %s", temp_dir, cleanup_error)
