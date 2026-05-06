import logging
import os
import shutil
import tempfile
from typing import Any

from worker.runners import CurlRunner, TarRunner

PICTURE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}


class DownloadService:
    def __init__(
        self,
        curl_runner: CurlRunner,
        tar_runner: TarRunner,
        download_path: str,
        pictures_path: str,
        videos_path: str,
    ) -> None:
        self.curl_runner = curl_runner
        self.tar_runner = tar_runner
        self.download_path = download_path
        self.pictures_path = pictures_path
        self.videos_path = videos_path
        self.logger = logging.getLogger(self.__class__.__name__)

    async def download_chunk(self, task: dict[str, Any]) -> tuple[bool, str]:
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

        output_file = f"takeout-{timestamp}Z-{chunk_num_str}.tgz"
        output_path = os.path.join(self.download_path, output_file)
        url = (
            f"https://takeout-download.usercontent.google.com/download/{output_file}"
            f"?j={job_id}&i={chunk_index - 1}&user={user_id}&authuser={auth_user}"
        )

        headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en-US,en;q=0.9",
            "priority": "u=0, i",
            "referer": "https://takeout.google.com/",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-site",
            "upgrade-insecure-requests": "1",
            "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "cookie": cookie,
        }

        success = await self.curl_runner.download(url, output_path, headers)

        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
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
        output_file = f"takeout-{timestamp}Z-{chunk_num_str}.tgz"
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
