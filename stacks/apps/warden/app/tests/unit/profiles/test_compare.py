from __future__ import annotations

from copy import deepcopy

import pytest

from tests.profile_data import REMOTE_FORMAT, REMOTE_PROFILE
from warden.profiles.models import ProfileDocument
from warden.profiles.compare import compare_profiles, select_profiles
from warden.profiles.export import export_documents


@pytest.fixture()
def documents() -> list[ProfileDocument]:
    return list(export_documents("radarr", [deepcopy(REMOTE_PROFILE)], [deepcopy(REMOTE_FORMAT)], ()))


def test_identical_configuration_has_no_differences(documents: list[ProfileDocument]) -> None:
    assert compare_profiles("radarr", documents, [REMOTE_PROFILE], [REMOTE_FORMAT]) == {
        "source": "radarr", "profiles": ["HD"], "changes": [], "conflicts": [],
    }


def test_remote_ids_do_not_affect_comparison(documents: list[ProfileDocument]) -> None:
    profile, custom_format = deepcopy(REMOTE_PROFILE), deepcopy(REMOTE_FORMAT)
    profile["id"] = 99
    profile["formatItems"][0]["format"] = custom_format["id"] = 88
    profile["cutoff"] = profile["items"][1]["id"] = 77
    assert compare_profiles("radarr", documents, [profile], [custom_format])["changes"] == []


def test_ignores_documentation_and_normalizes_field_representation(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["description"] = "For sharing"
    documents[1].data["trash_id"] = "community-origin"
    documents[1].data["trash_scores"] = {"default": 123}
    documents[1].data["specifications"][0]["fields"] = [{"name": "value", "value": "Preferred"}]
    assert compare_profiles("radarr", documents, [REMOTE_PROFILE], [REMOTE_FORMAT])["changes"] == []


def test_specification_order_is_not_behavior(documents: list[ProfileDocument]) -> None:
    other = {"name": "Resolution", "implementation": "ResolutionSpecification", "negate": False,
             "required": True, "fields": {"value": 1080}}
    documents[1].data["specifications"].append(other)
    remote = deepcopy(REMOTE_FORMAT)
    remote["specifications"].insert(0, {**other, "fields": [{"name": "value", "value": 1080}]})
    assert compare_profiles("radarr", documents, [REMOTE_PROFILE], [remote])["changes"] == []


def test_quality_precedence_and_group_order_are_preserved(documents: list[ProfileDocument]) -> None:
    desired = documents[0].data["quality_profiles"][0]
    desired["qualities"].reverse()
    desired["qualities"][1]["qualities"].reverse()
    changes = compare_profiles("radarr", documents, [REMOTE_PROFILE], [REMOTE_FORMAT])["changes"]
    assert len(changes) == 1
    assert changes[0]["field"] == "qualities"
    assert changes[0]["desired"] == desired["qualities"]


def test_enabled_default_and_omitted_language_are_unmanaged(documents: list[ProfileDocument]) -> None:
    profile = documents[0].data["quality_profiles"][0]
    del profile["qualities"][0]["enabled"]
    del profile["language"]
    assert compare_profiles("radarr", documents, [REMOTE_PROFILE], [REMOTE_FORMAT])["changes"] == []


def test_omitted_scores_mean_zero_without_removing_formats(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["custom_format_scores"] = {}
    assert compare_profiles("radarr", documents, [REMOTE_PROFILE], [REMOTE_FORMAT])["changes"] == [{
        "kind": "profile", "name": "HD", "field": "custom_format_scores.Preferred", "current": 100, "desired": 0,
    }]


def test_unrelated_zero_scores_and_profiles_do_not_drift(documents: list[ProfileDocument]) -> None:
    remote = deepcopy(REMOTE_PROFILE)
    remote["formatItems"].append({"format": 18, "name": "Unused", "score": 0})
    unused = {**REMOTE_FORMAT, "id": 18, "name": "Unused", "futureBehavior": True}
    other = {**REMOTE_PROFILE, "id": 99, "name": "Other", "futureProfileBehavior": True}
    assert compare_profiles("radarr", documents, [remote, other], [REMOTE_FORMAT, unused])["changes"] == []


def test_changed_upgrade_threshold_reports_field(documents: list[ProfileDocument]) -> None:
    documents[0].data["quality_profiles"][0]["upgrade"]["until_score"] = 2000
    assert compare_profiles("radarr", documents, [REMOTE_PROFILE], [REMOTE_FORMAT])["changes"] == [{
        "kind": "profile", "name": "HD", "field": "upgrade.until_score", "current": 1000, "desired": 2000,
    }]


def test_existing_unassigned_format_is_compared(documents: list[ProfileDocument]) -> None:
    remote = deepcopy(REMOTE_PROFILE)
    remote["formatItems"] = []
    changes = compare_profiles("radarr", documents, [remote], [REMOTE_FORMAT])["changes"]
    assert changes == [{"kind": "profile", "name": "HD", "field": "custom_format_scores.Preferred", "current": 0, "desired": 100}]


def test_selecting_all_affected_profiles_resolves_shared_conflict(documents: list[ProfileDocument]) -> None:
    other = deepcopy(REMOTE_PROFILE)
    other.update(id=46, name="Other")
    other_documents = export_documents("radarr", [other], [REMOTE_FORMAT], ())
    documents.append(other_documents[0])
    documents[1].data["specifications"][0]["fields"]["value"] = "New pattern"
    result = compare_profiles("radarr", documents, [REMOTE_PROFILE, other], [REMOTE_FORMAT])
    assert result["profiles"] == ["HD", "Other"]
    assert result["conflicts"] == []
    assert len(result["changes"]) == 1


def test_duplicate_remote_names_are_errors(documents: list[ProfileDocument]) -> None:
    with pytest.raises(ValueError, match="duplicate remote profile"):
        compare_profiles("radarr", documents, [REMOTE_PROFILE, REMOTE_PROFILE], [REMOTE_FORMAT])


def test_duplicate_condition_names_are_errors(documents: list[ProfileDocument]) -> None:
    documents[1].data["specifications"].append(deepcopy(documents[1].data["specifications"][0]))
    with pytest.raises(ValueError, match="duplicate condition"):
        compare_profiles("radarr", documents, [REMOTE_PROFILE], [REMOTE_FORMAT])


def test_profile_selection_is_exact_and_scoped(documents: list[ProfileDocument]) -> None:
    assert select_profiles("radarr", documents, None) == ["HD"]
    assert select_profiles("radarr", documents, ["HD", "HD"]) == ["HD"]
    assert select_profiles("radarr", documents, []) == []
    with pytest.raises(ValueError, match="unknown profile 'hd'"):
        select_profiles("radarr", documents, ["hd"])
    with pytest.raises(ValueError, match="no compatible profiles"):
        select_profiles("sonarr", documents, None)


def test_sonarr_profile_comparison() -> None:
    profile = deepcopy(REMOTE_PROFILE)
    del profile["language"]
    documents = export_documents("sonarr", [profile], [REMOTE_FORMAT], ())
    assert compare_profiles("sonarr", documents, [profile], [REMOTE_FORMAT]) == {
        "source": "sonarr", "profiles": ["HD"], "changes": [], "conflicts": [],
    }
