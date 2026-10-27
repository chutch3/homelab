from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from warden.profiles.catalog import Document, validate_references
from warden.profiles.reading import CatalogFile, CatalogFiles, CatalogReader, DocumentCodec, encode_catalog


class TestCatalogReader:
    @pytest.fixture()
    def subject(self) -> CatalogReader:
        files = Mock(spec=CatalogFiles)
        files.entries.return_value = [CatalogFile("radarr", "profiles", "radarr/profiles/one.yml")]
        files.read.return_value = b"one"
        codec = Mock(spec=DocumentCodec)
        codec.decode.return_value = Document("radarr", "profiles", "radarr/profiles/one.yml", {})
        return CatalogReader(files, codec, Mock(spec=validate_references))

    def test_reads_decodes_and_validates_without_a_byte_limit(self, subject: CatalogReader) -> None:
        result = subject.load(Path("/catalog"))
        entry = CatalogFile("radarr", "profiles", "radarr/profiles/one.yml")
        assert result == (Document("radarr", "profiles", entry.path, {}),)
        subject.files.entries.assert_called_once_with(Path("/catalog"))
        subject.files.read.assert_called_once_with(Path("/catalog"), entry, None)
        subject.codec.decode.assert_called_once_with(entry, b"one")
        subject.validate.assert_called_once_with(result)

    def test_budget_is_shared_between_files_and_accepts_exact_boundary(self, subject: CatalogReader) -> None:
        first = CatalogFile("radarr", "profiles", "radarr/profiles/one.yml")
        second = CatalogFile("radarr", "custom_formats", "radarr/custom_formats/two.json")
        subject.files.entries.return_value = [first, second]
        subject.files.read.side_effect = [b"one", b"four"]
        documents = (Document(first.source, first.kind, first.path, {}), Document(second.source, second.kind, second.path, {}))
        subject.codec.decode.side_effect = documents
        assert subject.load(Path("/catalog"), max_bytes=7) == documents
        assert subject.files.read.call_args_list == [
            ((Path("/catalog"), first, 8), {}), ((Path("/catalog"), second, 5), {}),
        ]
        subject.validate.assert_called_once_with(documents)

    def test_oversized_file_stops_before_decoding_or_further_reads(self, subject: CatalogReader) -> None:
        subject.files.read.return_value = b"four"
        with pytest.raises(ValueError, match="radarr/profiles/one.yml: catalog byte budget exceeded"):
            subject.load(Path("/catalog"), max_bytes=3)
        assert subject.files.read.call_count == 1
        subject.codec.decode.assert_not_called()
        subject.validate.assert_not_called()

    @pytest.mark.parametrize("error", [ValueError("bad field"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")])
    def test_decode_errors_name_the_file(self, subject: CatalogReader, error: Exception) -> None:
        subject.codec.decode.side_effect = error
        with pytest.raises(ValueError, match="radarr/profiles/one.yml:"):
            subject.load(Path("/catalog"))
        subject.validate.assert_not_called()

    def test_read_error_stops_before_decoding(self, subject: CatalogReader) -> None:
        subject.files.read.side_effect = OSError("read failed")
        with pytest.raises(ValueError, match="radarr/profiles/one.yml: read failed"):
            subject.load(Path("/catalog"))
        subject.codec.decode.assert_not_called()
        subject.validate.assert_not_called()

    def test_empty_input_still_runs_catalog_validation(self, subject: CatalogReader) -> None:
        subject.files.entries.return_value = []
        subject.validate.side_effect = ValueError("catalog contains no profiles")
        with pytest.raises(ValueError, match="catalog contains no profiles"):
            subject.load(Path("/catalog"))
        subject.validate.assert_called_once_with(())
        subject.files.read.assert_not_called()


@pytest.mark.parametrize("path", ["/absolute.yml", "../escape.yml", "radarr/profiles/../../escape.yml", "sonarr/profiles/hd.yml"])
def test_encoding_rejects_unsafe_paths_before_using_codec(path: str) -> None:
    codec = Mock(spec=DocumentCodec)
    with pytest.raises(ValueError, match="invalid catalog path"):
        encode_catalog([Document("radarr", "profiles", path, {})], codec)
    codec.encode.assert_not_called()


def test_encoding_uses_codec_for_the_given_documents() -> None:
    document = Document("radarr", "profiles", "radarr/profiles/hd.yml", {})
    codec = Mock(spec=DocumentCodec)
    codec.encode.return_value = b"encoded"
    assert encode_catalog([document], codec) == {document.path: b"encoded"}
    codec.encode.assert_called_once_with(document)
