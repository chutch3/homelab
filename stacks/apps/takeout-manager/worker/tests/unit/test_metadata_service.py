import pytest
from unittest.mock import AsyncMock
from pathlib import Path

from worker.services import MetadataService
from worker.runners import TarRunner, GpthRunner


class TestMetadataService:
    @pytest.fixture
    def mock_tar_runner(self):
        return AsyncMock(spec=TarRunner)

    @pytest.fixture
    def mock_gpth_runner(self):
        return AsyncMock(spec=GpthRunner)

    @pytest.fixture
    def subject(self, mock_tar_runner, mock_gpth_runner, tmp_path):
        return MetadataService(
            tar_runner=mock_tar_runner,
            gpth_runner=mock_gpth_runner,
            download_path=str(tmp_path / "downloads"),
            pictures_path=str(tmp_path / "pictures"),
            videos_path=str(tmp_path / "videos"),
        )

    @pytest.fixture
    def downloads_dir(self, tmp_path):
        d = tmp_path / "downloads"
        d.mkdir()
        return d

    @pytest.fixture
    def pictures_dir(self, tmp_path):
        d = tmp_path / "pictures"
        d.mkdir()
        return d

    @pytest.fixture
    def videos_dir(self, tmp_path):
        d = tmp_path / "videos"
        d.mkdir()
        return d

    @pytest.mark.asyncio
    async def test_missing_params(self, subject):
        success, message = await subject.process_job_metadata({"id": 1, "type": "metadata", "params": {}})
        assert success is False
        assert message == "Missing required metadata parameters"

    @pytest.mark.asyncio
    async def test_reextracts_every_chunk_archive(
        self, subject, mock_tar_runner, mock_gpth_runner, downloads_dir, pictures_dir, videos_dir
    ):
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"a1")
        (downloads_dir / "takeout-20240101T120000Z-1-002.tgz").write_bytes(b"a2")
        mock_tar_runner.extract.return_value = True
        mock_gpth_runner.process.return_value = True

        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 2},
        }

        await subject.process_job_metadata(task)

        assert mock_tar_runner.extract.call_count == 2
        extracted_archives = {call.args[0] for call in mock_tar_runner.extract.call_args_list}
        assert extracted_archives == {
            str(downloads_dir / "takeout-20240101T120000Z-1-001.tgz"),
            str(downloads_dir / "takeout-20240101T120000Z-1-002.tgz"),
        }
        # Every chunk extracts into the same combined raw directory.
        raw_dirs = {call.args[1] for call in mock_tar_runner.extract.call_args_list}
        assert len(raw_dirs) == 1

    @pytest.mark.asyncio
    async def test_returns_failure_when_an_archive_is_missing(self, subject, downloads_dir):
        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }

        success, message = await subject.process_job_metadata(task)

        assert success is False
        assert "Archive not found" in message

    @pytest.mark.asyncio
    async def test_returns_failure_when_reextraction_fails(
        self, subject, mock_tar_runner, downloads_dir
    ):
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"a1")
        mock_tar_runner.extract.return_value = False

        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }

        success, message = await subject.process_job_metadata(task)

        assert success is False
        assert "chunk 1" in message

    @pytest.mark.asyncio
    async def test_returns_failure_when_gpth_fails(
        self, subject, mock_tar_runner, mock_gpth_runner, downloads_dir
    ):
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"a1")
        mock_tar_runner.extract.return_value = True
        mock_gpth_runner.process.return_value = False

        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }

        success, message = await subject.process_job_metadata(task)

        assert success is False
        assert message == "GPTH processing failed"

    @pytest.mark.asyncio
    async def test_splits_gpth_output_into_pictures_and_videos_preserving_date_path(
        self, subject, mock_tar_runner, mock_gpth_runner, downloads_dir, pictures_dir, videos_dir
    ):
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"a1")
        mock_tar_runner.extract.return_value = True

        async def simulate_gpth(input_dir, output_dir):
            dated = Path(output_dir) / "2024" / "01"
            dated.mkdir(parents=True, exist_ok=True)
            (dated / "photo.jpg").write_bytes(b"exif photo")
            (dated / "clip.mp4").write_bytes(b"exif video")
            (dated / "metadata.json").write_bytes(b"{}")  # neither picture nor video — ignored
            return True

        mock_gpth_runner.process.side_effect = simulate_gpth

        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }

        success, message = await subject.process_job_metadata(task)

        assert success is True
        assert message == "Processed metadata for 1 pictures and 1 videos"
        assert (pictures_dir / "2024" / "01" / "photo.jpg").exists()
        assert (videos_dir / "2024" / "01" / "clip.mp4").exists()
        assert not (pictures_dir / "metadata.json").exists()
        assert not (videos_dir / "metadata.json").exists()

    @pytest.mark.asyncio
    async def test_deletes_superseded_flat_copy_from_original_extraction(
        self, subject, mock_tar_runner, mock_gpth_runner, downloads_dir, pictures_dir, videos_dir
    ):
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"a1")
        (pictures_dir / "photo.jpg").write_bytes(b"old flat copy without real exif")
        mock_tar_runner.extract.return_value = True

        async def simulate_gpth(input_dir, output_dir):
            dated = Path(output_dir) / "2024" / "01"
            dated.mkdir(parents=True, exist_ok=True)
            (dated / "photo.jpg").write_bytes(b"exif-embedded copy")
            return True

        mock_gpth_runner.process.side_effect = simulate_gpth

        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }

        await subject.process_job_metadata(task)

        assert not (pictures_dir / "photo.jpg").exists()  # flat copy gone
        moved = pictures_dir / "2024" / "01" / "photo.jpg"
        assert moved.exists()
        assert moved.read_bytes() == b"exif-embedded copy"  # the new, dated copy survives

    @pytest.mark.asyncio
    async def test_returns_failure_message_on_unexpected_exception_during_split(
        self, subject, mock_tar_runner, mock_gpth_runner, downloads_dir
    ):
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"a1")
        mock_tar_runner.extract.return_value = True

        async def simulate_gpth(input_dir, output_dir):
            dated = Path(output_dir) / "2024" / "01"
            dated.mkdir(parents=True, exist_ok=True)
            (dated / "photo.jpg").write_bytes(b"exif photo")
            return True

        mock_gpth_runner.process.side_effect = simulate_gpth

        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }

        with pytest.MonkeyPatch.context() as mp:
            def raise_oserror(*args, **kwargs):
                raise OSError("disk full")
            mp.setattr("shutil.move", raise_oserror)

            success, message = await subject.process_job_metadata(task)

        assert success is False
        assert "disk full" in message

    @pytest.mark.asyncio
    async def test_cleans_up_temp_directories_on_success(
        self, subject, mock_tar_runner, mock_gpth_runner, downloads_dir
    ):
        (downloads_dir / "takeout-20240101T120000Z-1-001.tgz").write_bytes(b"a1")
        mock_tar_runner.extract.return_value = True

        captured_dirs = {}

        async def capture_extract(archive_path, raw_dir):
            captured_dirs["raw"] = raw_dir
            return True

        mock_tar_runner.extract.side_effect = capture_extract

        async def capture_gpth(input_dir, output_dir):
            captured_dirs["gpth_output"] = output_dir
            return True

        mock_gpth_runner.process.side_effect = capture_gpth

        task = {
            "id": 1, "type": "metadata",
            "params": {"job_id": "test-job", "timestamp": "20240101T120000", "total_chunks": 1},
        }

        await subject.process_job_metadata(task)

        assert not Path(captured_dirs["raw"]).exists()
        assert not Path(captured_dirs["gpth_output"]).exists()
