from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from unittest.mock import Mock

import pytest

from warden.profiles.models import ProfileDocument
from warden.profiles.validation import validate_references
from warden.profiles.reading import ProfileFile, ProfileFiles, read_profiles, DocumentCodec, encode_profiles


@pytest.fixture()
def files() -> ProfileFiles:
    files = Mock(spec=ProfileFiles)
    files.entries.return_value = [ProfileFile("radarr", "profiles", "radarr/profiles/one.yml")]
    files.read.return_value = b"one"
    return files


@pytest.fixture()
def codec() -> DocumentCodec:
    codec = Mock(spec=DocumentCodec)
    codec.decode.return_value = ProfileDocument("radarr", "profiles", "radarr/profiles/one.yml", {})
    return codec


@pytest.fixture()
def validate() -> Callable[[Sequence[ProfileDocument]], None]:
    return Mock(spec=validate_references)


def test_read_profiles_reads_decodes_and_validates_without_a_byte_limit(files: ProfileFiles, codec: DocumentCodec, validate: Callable[[Sequence[ProfileDocument]], None]) -> None:
    result = read_profiles(Path("/catalog"), files, codec, validate)
    entry = ProfileFile("radarr", "profiles", "radarr/profiles/one.yml")
    assert result == (ProfileDocument("radarr", "profiles", entry.path, {}),)
    files.entries.assert_called_once_with(Path("/catalog"))
    files.read.assert_called_once_with(Path("/catalog"), entry, None)
    codec.decode.assert_called_once_with(entry, b"one")
    validate.assert_called_once_with(result)


def test_read_profiles_budget_is_shared_between_files_and_accepts_exact_boundary(files: ProfileFiles, codec: DocumentCodec, validate: Callable[[Sequence[ProfileDocument]], None]) -> None:
    first = ProfileFile("radarr", "profiles", "radarr/profiles/one.yml")
    second = ProfileFile("radarr", "custom_formats", "radarr/custom_formats/two.json")
    files.entries.return_value = [first, second]
    files.read.side_effect = [b"one", b"four"]
    documents = (ProfileDocument(first.source, first.kind, first.path, {}), ProfileDocument(second.source, second.kind, second.path, {}))
    codec.decode.side_effect = documents
    assert read_profiles(Path("/catalog"), files, codec, validate, max_bytes=7) == documents
    assert files.read.call_args_list == [
        ((Path("/catalog"), first, 8), {}), ((Path("/catalog"), second, 5), {}),
    ]
    validate.assert_called_once_with(documents)


def test_read_profiles_oversized_file_stops_before_decoding_or_further_reads(files: ProfileFiles, codec: DocumentCodec, validate: Callable[[Sequence[ProfileDocument]], None]) -> None:
    files.read.return_value = b"four"
    with pytest.raises(ValueError, match="radarr/profiles/one.yml: profile byte budget exceeded"):
        read_profiles(Path("/catalog"), files, codec, validate, max_bytes=3)
    assert files.read.call_count == 1
    codec.decode.assert_not_called()
    validate.assert_not_called()


@pytest.mark.parametrize("error", [ValueError("bad field"), UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid")])
def test_read_profiles_decode_errors_name_the_file(files: ProfileFiles, codec: DocumentCodec, validate: Callable[[Sequence[ProfileDocument]], None], error: Exception) -> None:
    codec.decode.side_effect = error
    with pytest.raises(ValueError, match="radarr/profiles/one.yml:"):
        read_profiles(Path("/catalog"), files, codec, validate)
    validate.assert_not_called()


def test_read_profiles_read_error_stops_before_decoding(files: ProfileFiles, codec: DocumentCodec, validate: Callable[[Sequence[ProfileDocument]], None]) -> None:
    files.read.side_effect = OSError("read failed")
    with pytest.raises(ValueError, match="radarr/profiles/one.yml: read failed"):
        read_profiles(Path("/catalog"), files, codec, validate)
    codec.decode.assert_not_called()
    validate.assert_not_called()


def test_read_profiles_empty_input_still_runs_catalog_validation(files: ProfileFiles, codec: DocumentCodec, validate: Callable[[Sequence[ProfileDocument]], None]) -> None:
    files.entries.return_value = []
    validate.side_effect = ValueError("configuration contains no profiles")
    with pytest.raises(ValueError, match="configuration contains no profiles"):
        read_profiles(Path("/catalog"), files, codec, validate)
    validate.assert_called_once_with(())
    files.read.assert_not_called()


@pytest.mark.parametrize("path", ["/absolute.yml", "../escape.yml", "radarr/profiles/../../escape.yml", "sonarr/profiles/hd.yml"])
def test_encode_profiles_rejects_unsafe_paths_before_using_codec(path: str) -> None:
    codec = Mock(spec=DocumentCodec)
    with pytest.raises(ValueError, match="invalid profile path"):
        encode_profiles([ProfileDocument("radarr", "profiles", path, {})], codec)
    codec.encode.assert_not_called()


def test_encode_profiles_uses_codec_for_the_given_documents() -> None:
    document = ProfileDocument("radarr", "profiles", "radarr/profiles/hd.yml", {})
    codec = Mock(spec=DocumentCodec)
    codec.encode.return_value = b"encoded"
    assert encode_profiles([document], codec) == {document.path: b"encoded"}
    codec.encode.assert_called_once_with(document)
