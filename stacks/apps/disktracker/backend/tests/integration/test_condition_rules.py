"""The rules that read a condition from listing text, and reading pasted listing text."""

from fastapi.testclient import TestClient

from disktracker.main import create_app

SEEDED_CONDITION_RULES = [
    {"pattern": r"\bmanufacturer recertified\b", "condition": "manufacturer_recertified"},
    {"pattern": r"\bseller refurbished\b", "condition": "refurbished"},
    {"pattern": r"\bopen box\b", "condition": "used"},
    {"pattern": r"\brecertified\b", "condition": "refurbished"},
    {"pattern": r"\brefurbished\b", "condition": "refurbished"},
    {"pattern": r"\brenewed\b", "condition": "refurbished"},
    {"pattern": r"\bused\b", "condition": "used"},
    {"pattern": r"\bnew\b", "condition": "new"},
]


def test_condition_rules_are_seeded_replaced_in_order_and_read_pasted_text(
    database_url: str,
) -> None:
    pasted = {"text": "Seagate Exos X18 ST18000NM000J 18TB Pre-Owned, like new\n$199.99"}
    pre_owned = {"pattern": r"\bpre-?owned\b", "condition": "used"}
    with TestClient(create_app()) as client:
        seeded = client.get("/api/condition-rules").json()
        before = client.post("/api/listing-text", json=pasted).json()["condition"]
        replaced = client.put("/api/condition-rules", json=[pre_owned, *seeded])
        after = client.post("/api/listing-text", json=pasted).json()["condition"]
        listed = client.get("/api/condition-rules").json()

    assert seeded == SEEDED_CONDITION_RULES
    assert before == "new"
    assert replaced.status_code == 200, replaced.text
    # Earlier rules win: "Pre-Owned" is read before "new".
    assert (after, listed) == ("used", [pre_owned, *SEEDED_CONDITION_RULES])


def test_a_condition_rule_that_cannot_work_is_refused_where_it_is_and_nothing_is_replaced(
    database_url: str,
) -> None:
    """Which rules cannot work is the schema's (tests/unit/catalog/test_schemas.py)."""
    rule = {"pattern": "(unclosed", "condition": "used"}
    with TestClient(create_app()) as client:
        refused = client.put("/api/condition-rules", json=[SEEDED_CONDITION_RULES[0], rule])
        kept = client.get("/api/condition-rules").json()

    assert refused.status_code == 422
    assert [issue["loc"] for issue in refused.json()["detail"]] == [["body", 1, "pattern"]]
    assert kept == SEEDED_CONDITION_RULES


def test_pasted_listing_text_is_read_into_the_fields_of_an_offer(database_url: str) -> None:
    pasted = (
        "\n  Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive  \n"
        "Was $299.99\n$1,219.99\nIn stock\n"
    )
    with TestClient(create_app()) as client:
        read = client.post("/api/listing-text", json={"text": pasted})
        nothing = client.post("/api/listing-text", json={"text": "hello"})

    assert read.status_code == 200, read.text
    assert read.json() == {
        "title": "Seagate Exos X18 ST18000NM000J 18TB 7200RPM SATA Recertified Hard Drive",
        "mpn": "ST18000NM000J",
        "capacity_gb": 18000,
        "condition": "refurbished",
        "brand": "Seagate",
        "item_price_cents": 121999,
    }
    assert nothing.json() == {
        "title": "hello",
        "mpn": None,
        "capacity_gb": None,
        "condition": None,
        "brand": None,
        "item_price_cents": None,
    }
