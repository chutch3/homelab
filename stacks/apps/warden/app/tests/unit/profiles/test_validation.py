from __future__ import annotations

from copy import deepcopy

import pytest

from warden.profiles.models import ProfileDocument
from warden.profiles.validation import validate_references


@pytest.fixture()
def documents() -> list[ProfileDocument]:
    profile = {
        "name": "HD", "upgrade": {"until_quality": "WEB"},
        "qualities": [{"name": "WEB", "qualities": ["WEBDL-1080p", "WEBRip-1080p"]}],
        "custom_format_scores": {"Preferred": 100},
    }
    return [
        ProfileDocument("radarr", "profiles", "radarr/profiles/hd.yml", {"quality_profiles": [profile]}),
        ProfileDocument("radarr", "custom_formats", "radarr/custom_formats/preferred.json", {"name": "Preferred"}),
    ]


def test_accepts_same_names_in_distinct_applications(documents: list[ProfileDocument]) -> None:
    copies = [ProfileDocument("sonarr", d.kind, d.path.replace("radarr", "sonarr"), deepcopy(d.data)) for d in documents]
    assert validate_references([*documents, *copies]) is None


def test_duplicate_profiles_identify_both_files(documents: list[ProfileDocument]) -> None:
    duplicate = ProfileDocument("radarr", "profiles", "radarr/profiles/duplicate.yml", documents[0].data)
    with pytest.raises(ValueError, match="duplicate profile 'HD'.*hd.yml.*duplicate.yml"):
        validate_references([*documents, duplicate])


def test_duplicate_formats_identify_both_files(documents: list[ProfileDocument]) -> None:
    duplicate = ProfileDocument("radarr", "custom_formats", "radarr/custom_formats/duplicate.json", documents[1].data)
    with pytest.raises(ValueError, match="duplicate custom format 'Preferred'.*preferred.json.*duplicate.json"):
        validate_references([*documents, duplicate])


def test_missing_format_identifies_profile(documents: list[ProfileDocument]) -> None:
    with pytest.raises(ValueError, match="radarr/profiles/hd.yml.*unknown custom format 'Preferred'"):
        validate_references(documents[:1])


def test_requires_profiles() -> None:
    with pytest.raises(ValueError, match="no profiles"):
        validate_references([])


def test_rejects_quality_in_multiple_groups(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["qualities"].append({"name": "WEBDL-1080p"})
    with pytest.raises(ValueError, match="duplicate quality 'WEBDL-1080p'"):
        validate_references(documents)


def test_rejects_unknown_cutoff(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["upgrade"]["until_quality"] = "Missing"
    with pytest.raises(ValueError, match="cutoff 'Missing' is not an enabled quality or group"):
        validate_references(documents)


def test_rejects_disabled_cutoff(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["qualities"][0]["enabled"] = False
    with pytest.raises(ValueError, match="cutoff 'WEB' is not an enabled quality or group"):
        validate_references(documents)


def test_rejects_radarr_language_in_sonarr_profile(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["language"] = "Original"
    sonarr = [ProfileDocument("sonarr", d.kind, d.path.replace("radarr", "sonarr"), d.data) for d in documents]
    with pytest.raises(ValueError, match="language is only supported for Radarr"):
        validate_references(sonarr)


def test_group_label_can_match_a_member_quality(documents: list[ProfileDocument]) -> None:
    profile = documents[0].data["quality_profiles"][0]
    profile["qualities"][0]["name"] = "WEBDL-1080p"
    profile["upgrade"]["until_quality"] = "WEBDL-1080p"
    assert validate_references(documents) is None


def test_duplicate_group_labels_are_rejected_even_with_distinct_members(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["qualities"].append({"name": "WEB", "qualities": ["HDTV-1080p"]})
    with pytest.raises(ValueError, match="duplicate quality 'WEB'"):
        validate_references(documents)
