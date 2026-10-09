import pytest
from pydantic import ValidationError

from disktracker.specifications import Specifications


def test_unknown_by_default() -> None:
    assert Specifications().model_dump() == {
        "media_type": "unknown",
        "form_factor": "unknown",
        "interface": "unknown",
        "recording_type": "unknown",
        "intended_use": [],
    }


def test_repeated_intended_uses_are_kept_once() -> None:
    specs = Specifications.model_validate({"intended_use": ["nas", "enterprise", "nas"]})
    assert specs.intended_use == ["nas", "enterprise"]


@pytest.mark.parametrize(
    ("data", "field"),
    [
        ({"media_type": "floppy"}, "media_type"),
        ({"form_factor": "5_25"}, "form_factor"),
        ({"interface": "sata-express"}, "interface"),
        ({"recording_type": {"value": "cmr"}}, "recording_type"),
        ({"intended_use": ["unknown"]}, "intended_use"),
        ({"smr_management": "host_managed"}, "smr_management"),
    ],
)
def test_invalid_specifications_are_rejected(data: dict[str, object], field: str) -> None:
    with pytest.raises(ValidationError) as error:
        Specifications.model_validate(data)
    assert error.value.errors()[0]["loc"][0] == field
