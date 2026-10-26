from __future__ import annotations

from copy import deepcopy

import pytest

from tests.integration.test_profile_dump import REMOTE_FORMAT, REMOTE_PROFILE
from warden.profiles.export import export_documents
from warden.profiles.storage import require_local_filesystem


def test_export_resolves_names_and_preserves_quality_precedence() -> None:
    documents = export_documents("radarr", [REMOTE_PROFILE], [REMOTE_FORMAT], ())
    assert documents[0].data == {
        "schema_version": 1,
        "quality_profiles": [{
            "name": "HD", "upgrade": {"allowed": True, "until_quality": "WEB 1080p", "until_score": 1000},
            "min_format_score": 0, "min_upgrade_format_score": 1,
            "qualities": [
                {"name": "WEB 1080p", "enabled": True, "qualities": ["WEBDL-1080p", "WEBRip-1080p"]},
                {"name": "SDTV", "enabled": False},
            ],
            "custom_format_scores": {"Preferred": 100}, "language": "Original",
        }],
    }
    assert documents[1].data == {
        "name": "Preferred", "includeCustomFormatWhenRenaming": False,
        "specifications": [{
            "name": "Preferred release", "implementation": "ReleaseTitleSpecification",
            "negate": False, "required": True, "fields": {"value": "Preferred"},
        }],
    }


def test_export_sonarr_without_radarr_language() -> None:
    profile = deepcopy(REMOTE_PROFILE)
    del profile["language"]
    documents = export_documents("sonarr", [profile], [REMOTE_FORMAT], ("HD",))
    assert documents[0].source == "sonarr"
    assert "language" not in documents[0].data["quality_profiles"][0]


def test_export_rejects_unknown_behavioral_fields() -> None:
    profile = {**REMOTE_PROFILE, "futureBehavior": True}
    with pytest.raises(ValueError, match="unsupported.*futureBehavior"):
        export_documents("radarr", [profile], [REMOTE_FORMAT], ())


def test_export_rejects_missing_dependency() -> None:
    with pytest.raises(ValueError, match="missing custom format ID 17"):
        export_documents("radarr", [REMOTE_PROFILE], [], ())


def test_export_rejects_empty_instance() -> None:
    with pytest.raises(ValueError, match="no profiles"):
        export_documents("radarr", [], [], ())


def test_export_excludes_unused_formats() -> None:
    documents = export_documents("radarr", [REMOTE_PROFILE], [REMOTE_FORMAT, {**REMOTE_FORMAT, "id": 99, "name": "Unused"}], ())
    assert [d.data["name"] for d in documents if d.kind == "custom_formats"] == ["Preferred"]


@pytest.mark.parametrize("filesystem", ["ocfs2", "nfs4", "cifs", "overlay", "unknown"])
def test_rejects_shared_or_unverified_output_filesystems(filesystem: str) -> None:
    mounts = f"1 0 0:1 / / rw - {filesystem} storage rw\n"
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/output/catalog", mounts)


def test_accepts_local_mount_nested_under_shared_mount() -> None:
    mounts = "1 0 0:1 / / rw - ocfs2 storage rw\n2 1 0:2 / /local rw - tmpfs tmpfs rw\n"
    assert require_local_filesystem("/local/catalog", mounts) is None


def test_mount_prefix_must_end_at_path_boundary() -> None:
    mounts = "1 0 0:1 / / rw - ocfs2 storage rw\n2 1 0:2 / /local rw - tmpfs tmpfs rw\n"
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/local-other/catalog", mounts)


def test_rejects_unknown_mounts() -> None:
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/output/catalog", "")


def test_conflicting_mounts_at_same_path_fail_closed() -> None:
    mounts = "1 0 0:1 / / rw - tmpfs tmpfs rw\n2 1 0:2 / / rw - ocfs2 storage rw\n"
    with pytest.raises(ValueError, match="verified local filesystem"):
        require_local_filesystem("/output/catalog", mounts)
