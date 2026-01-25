import asyncio
import logging
import subprocess


class CurlRunner:
    """A wrapper for curl commands with automatic retry logic."""

    def __init__(self, max_retries=3):
        self.max_retries = max_retries
        self.logger = logging.getLogger(self.__class__.__name__)

    async def download(self, url: str, output_path: str, headers: dict) -> bool:
        """
        Download a file using curl with automatic retry on network failures.

        Args:
            url: The URL to download from
            output_path: Where to save the downloaded file
            headers: Dictionary of HTTP headers to include

        Returns:
            bool: True if download succeeded, False otherwise
        """
        # Construct header arguments
        header_args = []
        for key, value in headers.items():
            header_args.extend(["-H", f"{key}: {value}"])

        # Construct full curl command
        command = [
            "curl",
            url,
            "--compressed",
            "-C",
            "-",  # Resume support
            "--fail",
            "--silent",
            "--show-error",
            "--output",
            output_path,
            *header_args,
        ]

        # Retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                result = await asyncio.to_thread(
                    subprocess.run, command, check=True, capture_output=True, text=True
                )
                self.logger.info(f"Successfully downloaded to {output_path}")
                return True

            except subprocess.CalledProcessError as e:
                # Check for non-retryable errors (auth, not found)
                if e.returncode == 22:  # HTTP error
                    stderr = e.stderr or ""
                    if "401" in stderr or "404" in stderr:
                        self.logger.error(
                            f"Non-retryable error downloading: {stderr}"
                        )
                        return False

                # Network errors (code 56) or other transient errors - retry
                if attempt < self.max_retries:
                    self.logger.warning(
                        f"Download attempt {attempt} failed, retrying..."
                    )
                    await asyncio.sleep(1 * attempt)  # Exponential backoff
                else:
                    self.logger.error(
                        f"Download failed after {self.max_retries} attempts"
                    )
                    return False

        return False


class TarRunner:
    """A wrapper for tar commands with comprehensive error handling."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def extract(
        self, tgz_path: str, dest_dir: str, verify=False, list_files=False
    ):
        """
        Extract a .tgz file to a destination directory.

        Args:
            tgz_path: Path to the .tgz archive
            dest_dir: Directory to extract files into
            verify: If True, verify archive integrity before extraction
            list_files: If True, return a tuple of (success, list_of_files)

        Returns:
            bool: True if extraction succeeded, False otherwise
            tuple: (bool, list) if list_files=True
        """
        import os

        # Create destination directory if it doesn't exist
        try:
            os.makedirs(dest_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create directory {dest_dir}: {e}")
            return (False, []) if list_files else False

        # Optional verification step
        if verify:
            verify_command = ["tar", "-tzf", tgz_path]
            try:
                await asyncio.to_thread(
                    subprocess.run,
                    verify_command,
                    check=True,
                    capture_output=True,
                    text=True,
                )
                self.logger.info(f"Archive {tgz_path} verified successfully")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"Archive verification failed: {e.stderr}")
                return (False, []) if list_files else False

        # Construct tar extraction command
        command = ["tar", "-xzf", tgz_path, "-C", dest_dir]

        # If we need to list files, use -v for verbose output
        if list_files:
            command.insert(2, "-v")

        try:
            result = await asyncio.to_thread(
                subprocess.run, command, check=True, capture_output=True, text=True
            )
            self.logger.info(f"Successfully extracted {tgz_path} to {dest_dir}")

            if list_files:
                # Parse the extracted file list from stdout
                files = [
                    line.strip() for line in result.stdout.split("\n") if line.strip()
                ]
                return (True, files)
            return True

        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ""

            # Detect specific error types
            if "Unexpected EOF" in stderr or "damaged" in stderr:
                self.logger.error(f"Corrupted archive: {tgz_path}")
            elif "No such file or directory" in stderr:
                self.logger.error(f"Source file not found: {tgz_path}")
            elif "No space left on device" in stderr:
                self.logger.error(f"Insufficient disk space for extraction")
            elif "Permission denied" in stderr:
                self.logger.error(f"Permission denied accessing {dest_dir}")
            else:
                self.logger.error(f"Extraction failed: {stderr}")

            return (False, []) if list_files else False
