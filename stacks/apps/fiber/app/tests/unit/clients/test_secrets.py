from __future__ import annotations

from pathlib import Path

import pytest

from fiber.clients.secrets import SecretReader


class TestSecretReader:
    @pytest.fixture()
    def base_dir(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture()
    def subject(self, base_dir: Path) -> SecretReader:
        return SecretReader(base_dir=str(base_dir))

    def test_reads_secret_file(self, subject: SecretReader, base_dir: Path) -> None:
        (base_dir / "kenku_db_password").write_text("hunter2\n")
        assert subject.read("kenku_db_password") == "hunter2"

    def test_missing_secret_raises(self, subject: SecretReader) -> None:
        with pytest.raises(FileNotFoundError):
            subject.read("nope")
