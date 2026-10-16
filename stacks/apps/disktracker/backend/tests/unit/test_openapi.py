"""The published contract says which fields are always there: every field of what the API answers
with, defaults included, since it always gives them back; and of what it is sent, only those
without a default. Clients are generated from it, so they type each field as it is."""

from typing import Any

import pytest

from disktracker.main import create_app


@pytest.fixture
def schemas(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    # Nothing connects while the contract is made.
    monkeypatch.setenv("DISKTRACKER_DATABASE_URL", "postgresql+psycopg://unused@localhost/unused")
    found: dict[str, Any] = create_app().openapi()["components"]["schemas"]
    return found


def required(schemas: dict[str, Any], name: str) -> set[str]:
    return set(schemas[name].get("required", []))


def test_what_the_api_answers_with_has_every_field_it_always_gives_back(
    schemas: dict[str, Any],
) -> None:
    assert required(schemas, "SourcePreview") == {"status", "reason", "offer", "verdict", "notes"}
    # A model both sent and answered with is published once for each.
    assert required(schemas, "Specifications-Output") == {
        "media_type", "form_factor", "interface", "recording_type", "intended_use",
    }  # fmt: skip


def test_what_the_api_is_sent_needs_only_the_fields_without_a_default(
    schemas: dict[str, Any],
) -> None:
    assert required(schemas, "ManualSourcePreviewInput") == {"name", "kind"}
    assert required(schemas, "Specifications-Input") == set()
    assert {"provenance", "on_unmatched", "aliases"}.isdisjoint(required(schemas, "PriceInput"))
