import logging
import os
import shutil
import tempfile

DOWNLOAD_PATH = "/downloads"
PICTURES_PATH = "/pictures"
VIDEOS_PATH = "/videos"

# Media file extensions
PICTURE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".heic", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv", ".flv", ".webm"}


class DownloadService:
    """Service for downloading and extracting Google Takeout archives."""

    def __init__(self, curl_runner, tar_runner):
        self.curl_runner = curl_runner
        self.tar_runner = tar_runner
        self.logger = logging.getLogger(self.__class__.__name__)

    async def download_chunk(self, task):
        """
        Download a single takeout archive chunk.

        Args:
            task: Task dict with params containing download details

        Returns:
            tuple: (success: bool, message: str)
        """
        params = task.get("params", {})
        if not params:
            return False, "Task parameters are missing"

        chunk_index = params.get("chunk_index", 1)
        chunk_num_str = f"{chunk_index:03d}"
        timestamp = params.get("timestamp")
        job_id = params.get("job_id")
        user_id = params.get("user_id")
        auth_user = params.get("auth_user")
        cookie = params.get("cookie")

        output_file = f"takeout-{timestamp}Z-{chunk_num_str}.tgz"
        output_path = os.path.join(DOWNLOAD_PATH, output_file)
        url = f"https://takeout-download.usercontent.google.com/download/{output_file}?j={job_id}&i={chunk_index - 1}&user={user_id}&authuser={auth_user}"

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

        # Use the CurlRunner.download() method
        success = await self.curl_runner.download(url, output_path, headers)

        if success and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True, "Download successful"
        elif success:
            return False, "File not found or empty after download"
        else:
            return False, "Download failed"

    async def extract_chunk(self, task):
        """
        Extract a downloaded .tgz file and sort media files into appropriate directories.

        Args:
            task: Task dict with params containing extraction details

        Returns:
            tuple: (success: bool, message: str)
        """
        params = task.get("params", {})
        if not params:
            return False, "Task parameters are missing"

        job_id = params.get("job_id")  # Not used, but good to have
        timestamp = params.get("timestamp")
        chunk_index = params.get("chunk_index")

        if not all([timestamp, chunk_index]):
            return (
                False,
                "Missing required parameters for extraction (timestamp, chunk_index)",
            )

        chunk_num_str = f"{chunk_index:03d}"
        output_file = f"takeout-{timestamp}Z-{chunk_num_str}.tgz"

        tgz_path = os.path.join(DOWNLOAD_PATH, output_file)

        # Verify the archive exists
        if not os.path.exists(tgz_path):
            return False, f"Archive not found: {tgz_path}"

        # Create a temporary directory for extraction
        temp_extract_dir = tempfile.mkdtemp(prefix="extract_temp_")

        try:
            # Extract the archive
            success = await self.tar_runner.extract(tgz_path, temp_extract_dir)

            if not success:
                return False, "Failed to extract archive"

            # List all extracted files
            extracted_files = []
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    extracted_files.append(os.path.join(root, file))

            # Sort files by type and move to appropriate directories
            pictures_moved = 0
            videos_moved = 0

            for file_path in extracted_files:
                filename = os.path.basename(file_path)
                _, ext = os.path.splitext(filename)
                ext_lower = ext.lower()

                if ext_lower in PICTURE_EXTENSIONS:
                    # Move to pictures directory
                    os.makedirs(PICTURES_PATH, exist_ok=True)
                    dest_path = os.path.join(PICTURES_PATH, filename)
                    shutil.move(file_path, dest_path)
                    pictures_moved += 1
                elif ext_lower in VIDEO_EXTENSIONS:
                    # Move to videos directory
                    os.makedirs(VIDEOS_PATH, exist_ok=True)
                    dest_path = os.path.join(VIDEOS_PATH, filename)
                    shutil.move(file_path, dest_path)
                    videos_moved += 1
                # Ignore non-media files (like document.pdf)

            return True, f"Extracted {pictures_moved} pictures and {videos_moved} videos"

        except Exception as e:
            # Log the error and ensure cleanup happens
            self.logger.error(f"Extraction failed with exception: {e}")
            return False, f"Extraction error: {str(e)}"

        finally:
            # Clean up temporary directory - always runs even on error
            try:
                if os.path.exists(temp_extract_dir):
                    shutil.rmtree(temp_extract_dir)
            except Exception as cleanup_error:
                self.logger.warning(
                    f"Failed to cleanup temp directory {temp_extract_dir}: {cleanup_error}"
                )
