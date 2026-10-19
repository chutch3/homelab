"""Reading the catalog the way the Prices page does: drives filtered, ordered and paged by the
server with the filter options of every drive; a drive's offers and prices asked for by the
drive or offer, not by lists of ids; and what drives cost today as a report over every drive."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient
from test_api import post, price_payload, scraped_payload

from disktracker.main import create_app

NOW = datetime.now(UTC)


def ago(days: float) -> str:
    return (NOW - timedelta(days=days)).isoformat()


def record(client: TestClient, **fields: Any) -> str:
    """A price, recorded by hand unless said otherwise; the offer it is for."""
    response = post(client, "/api/prices", price_payload(**{"observed_at": ago(0.01), **fields}))
    assert response.status_code == 201, response.text
    offer_id: str = response.json()["offer_id"]
    return offer_id


def catalogue(client: TestClient) -> dict[str, str]:
    """Four drives, each named by its MPN, and the offers recorded for them.

    ST18000NM000J, Seagate, 18 TB, new: $180 at ServerPartDeals and $200 from Shop (other).
    WUH721212ALE6L4, Western Digital, 12 TB, recertified: $114 at GoHardDrive, SATA and CMR.
    ST14000NM001G, Seagate, 14 TB, used: $140 from Shop, sold out.
    ST8000VN004, no brand known, 8 TB, new: $160 from Old shop, last checked 20 days ago.
    """
    offers = {
        "spd": record(client, store="serverpartdeals", seller="", item_price_cents=18000,
                      shipping_cents=0, condition="new", title="Exos X18 18TB"),
        "shop": record(client, seller="Shop", item_price_cents=20000, shipping_cents=500,
                       condition="new", title="Exos X18"),
        "ghd": record(client, store="goharddrive", seller="", mpn="WUH721212ALE6L4",
                      capacity_gb=12000, condition="manufacturer_recertified",
                      item_price_cents=11400, shipping_cents=0, title="Ultrastar HC520 12TB",
                      specifications={"interface": "sata", "recording_type": "cmr"}),
        "used": record(client, seller="Shop", mpn="ST14000NM001G", capacity_gb=14000,
                       condition="used", item_price_cents=14000, in_stock=False,
                       title="Exos X16 14TB"),
        "stale": record(client, seller="Old shop", mpn="ST8000VN004", capacity_gb=8000,
                        condition="new", item_price_cents=16000, shipping_cents=0,
                        observed_at=ago(20), title="IronWolf 8TB"),
    }  # fmt: skip
    for mpn, brand in [
        ("ST18000NM000J", "Seagate"),
        ("WUH721212ALE6L4", "Western Digital"),
        ("ST14000NM001G", "Seagate"),
    ]:
        drive = client.get("/api/offers").json()
        drive_id = next(o["drive"]["id"] for o in drive if o["mpn"] == mpn)
        assert client.patch(f"/api/drives/{drive_id}", json={"brand": brand}).status_code == 200
    return offers


def mpns(page: dict[str, Any]) -> list[str]:
    return [row["drive"]["mpn"] for row in page["items"]]


def test_drives_are_served_a_page_at_a_time_cheapest_terabyte_first(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offers = catalogue(client)
        first = client.get("/api/drives", params={"limit": 2}).json()
        second = client.get("/api/drives", params={"limit": 2, "offset": 2}).json()
    # $9.50/TB (12 TB at $114), $10.00/TB (18 TB at $180), then $20.00/TB; the sold-out drive is
    # left out until asked for.
    assert mpns(first) + mpns(second) == ["WUH721212ALE6L4", "ST18000NM000J", "ST8000VN004"]
    assert (first["total"], first["limit"], first["offset"]) == (3, 2, 0)
    assert (second["offset"], len(second["items"])) == (2, 1)
    assert (first["offers"], first["sold_out"]) == (4, 1)
    assert datetime.fromisoformat(first["as_of"]) >= NOW
    seagate = first["items"][1]
    # A drive is shown by its cheapest offer in stock, with every offer of it that matches.
    assert seagate["representative"]["id"] == offers["spd"]
    assert {offer["id"] for offer in seagate["offers"]} == {offers["spd"], offers["shop"]}
    assert seagate["key"] == f"drive:{seagate['drive']['id']}"


def test_each_filter_option_counts_the_drives_choosing_it_would_give(database_url: str) -> None:
    """Counted with the search and every other filter as they are, but not the option's own
    group, so another option of it can be chosen instead. Every option the catalogue has is
    given, in the catalogue's order, however few it would give."""
    with TestClient(create_app()) as client:
        catalogue(client)
        narrowed = client.get(
            "/api/drives", params={"brand": "Western Digital", "limit": 1, "offset": 5}
        ).json()
        searched = client.get("/api/drives", params={"q": "ST18000NM000J"}).json()

    assert narrowed["total"] == 1 and narrowed["items"] == []
    # In stock unless asked otherwise: the used Exos X16 is sold out.
    assert narrowed["filter_options"] == {
        # Most drives in the catalogue first; drives no source has named come last, as unknown.
        "brands": [
            {"value": "Seagate", "drives": 1},
            {"value": "Western Digital", "drives": 1},
            {"value": "unknown", "drives": 1},
        ],
        "capacities": [
            {"value": 8000, "drives": 0},
            {"value": 12000, "drives": 1},
            {"value": 14000, "drives": 0},
            {"value": 18000, "drives": 0},
        ],
        "conditions": [
            {"value": "new", "drives": 0},
            {"value": "manufacturer_recertified", "drives": 1},
            {"value": "used", "drives": 0},
        ],
    }
    assert [(o["value"], o["drives"]) for o in searched["filter_options"]["conditions"]] == [
        ("new", 1), ("manufacturer_recertified", 0), ("used", 0),
    ]  # fmt: skip


def test_drives_are_narrowed_by_each_filter(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offers = catalogue(client)

        def found(**query: Any) -> list[str]:
            answer = client.get("/api/drives", params=query)
            assert answer.status_code == 200, answer.text
            return sorted(mpns(answer.json()))

        everything = ["ST14000NM001G", "ST18000NM000J", "ST8000VN004", "WUH721212ALE6L4"]
        assert found(in_stock=False) == everything
        # Search covers titles, MPNs, other MPNs and sellers, whatever their case.
        assert found(q="old SHOP") == ["ST8000VN004"]
        assert found(q="hc520") == ["WUH721212ALE6L4"]
        assert found(brand=["Seagate", "unknown"], in_stock=False) == [
            "ST14000NM001G", "ST18000NM000J", "ST8000VN004"
        ]  # fmt: skip
        assert found(capacity=[12000, 8000]) == ["ST8000VN004", "WUH721212ALE6L4"]
        assert found(condition="manufacturer_recertified") == ["WUH721212ALE6L4"]
        assert found(store="goharddrive") == ["WUH721212ALE6L4"]
        assert found(max_total_cents=16000) == ["ST8000VN004", "WUH721212ALE6L4"]
        assert found(interface="sata") == ["WUH721212ALE6L4"]
        assert found(interface="unknown") == ["ST18000NM000J", "ST8000VN004"]
        assert found(recording_type="cmr") == ["WUH721212ALE6L4"]
        # A drive with no intended use known is of unknown use.
        assert found(intended_use="unknown") == ["ST18000NM000J", "ST8000VN004", "WUH721212ALE6L4"]
        assert found(intended_use="nas") == []
        assert found(recent_only=True) == ["ST18000NM000J", "WUH721212ALE6L4"]
        # One drive, when it matches the rest: whether a drive just saved is hidden by them.
        seagate = client.get(f"/api/offers/{offers['spd']}").json()["drive"]["id"]
        assert found(drive_id=seagate) == ["ST18000NM000J"]
        assert found(drive_id=seagate, store="goharddrive") == []
        assert found(recent_only=True, recent_days=30) == [
            "ST18000NM000J", "ST8000VN004", "WUH721212ALE6L4"
        ]  # fmt: skip
        refused = [
            client.get("/api/drives", params=query).status_code
            for query in (
                {"sort": "cheapest"},
                {"limit": 0},
                {"limit": 501},
                {"offset": -1},
                {"condition": "mint"},
                {"interface": "ide"},
                {"max_total_cents": -1},
                {"range_days": 45},
            )
        ]
    assert refused == [422] * 8


def test_a_drive_is_placed_by_the_offers_that_match_in_the_order_asked_for(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        offers = catalogue(client)

        def order(sort: str) -> list[str]:
            return mpns(client.get("/api/drives", params={"sort": sort}).json())

        by_total = order("total-desc")
        by_capacity = order("capacity-asc")
        by_check = order("checked-asc")
        # Asked for its dearer store only, the 18 TB drive is shown by that offer.
        shop_only = client.get("/api/drives", params={"q": "shop", "in_stock": False}).json()
    assert by_total == ["ST18000NM000J", "ST8000VN004", "WUH721212ALE6L4"]
    assert by_capacity == ["ST8000VN004", "WUH721212ALE6L4", "ST18000NM000J"]
    assert by_check[0] == "ST8000VN004"
    rows = {row["drive"]["mpn"]: row for row in shop_only["items"]}
    assert rows["ST18000NM000J"]["representative"]["id"] == offers["shop"]
    # A drive no store has in stock comes after every drive that can be bought.
    assert mpns(shop_only)[-1] == "ST14000NM001G"


def test_the_lowest_prices_are_marked_across_every_drive_that_matches_not_the_page(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        offers = catalogue(client)
        page = client.get("/api/drives", params={"limit": 1, "offset": 2}).json()
    # Only offers in stock and checked recently can be lowest.
    assert page["lowest"] == {
        "total": [offers["ghd"]],
        "unit": [offers["ghd"]],
    }


def test_each_drive_comes_with_the_range_of_its_lowest_price_over_the_days_asked_for(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        mpn = "ST16000NM001G"
        common = {"seller": "", "store": "goharddrive", "mpn": mpn, "capacity_gb": 16000,
                  "condition": "new", "shipping_cents": 0}  # fmt: skip
        for days, cents in [(40, 20000), (10, 18000), (0.001, 18000)]:
            post(
                client,
                "/api/prices",
                price_payload(**common, item_price_cents=cents, observed_at=ago(days)),
            )
        answer = client.get("/api/drives", params={"range_days": 30})
        assert answer.status_code == 200, answer.text
        [row] = answer.json()["items"]
    # $200 held from the period's start until ten days ago, $180 since.
    assert row["range"] == {
        "today": 18000,
        "low": 18000,
        "high": 20000,
        "average": round((20000 * 20 + 18000 * 10) / 30),
        "days": 30,
    }


def test_a_drive_is_read_with_every_offer_of_it_in_any_condition(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offers = catalogue(client)
        recertified = record(client, store="goharddrive", seller="", condition="used",
                             item_price_cents=15000)  # fmt: skip
        drive_id = client.get(f"/api/offers/{offers['spd']}").json()["drive"]["id"]
        read = client.get(f"/api/drives/{drive_id}")
        missing = client.get(f"/api/drives/{uuid4()}")
    assert read.status_code == 200, read.text
    assert read.json()["drive"]["mpn"] == "ST18000NM000J"
    assert {offer["id"] for offer in read.json()["offers"]} == {
        offers["spd"],
        offers["shop"],
        recertified,
    }
    assert missing.status_code == 404


def test_prices_are_read_by_drive_or_offer_and_within_a_window(database_url: str) -> None:
    with TestClient(create_app()) as client:
        first = record(client, observed_at=ago(40), item_price_cents=20000)
        record(client, observed_at=ago(20), item_price_cents=19000)
        record(client, observed_at=ago(5), item_price_cents=18000)
        other = record(client, seller="Other seller", observed_at=ago(3), item_price_cents=17000)
        record(client, mpn="WUH721212ALE6L4", capacity_gb=12000, item_price_cents=9000)
        drive_id = client.get(f"/api/offers/{first}").json()["drive"]["id"]

        def prices(**query: Any) -> list[int]:
            answer = client.get("/api/prices", params=query)
            assert answer.status_code == 200, answer.text
            return [price["item_price_cents"] for price in answer.json()["items"]]

        by_drive = client.get("/api/prices", params={"drive_id": drive_id}).json()
        windowed = prices(drive_id=drive_id, since=ago(10))
        bounded = prices(offer_id=first, since=ago(30), until=ago(10))
        paged = client.get("/api/prices", params={"drive_id": drive_id, "limit": 2, "offset": 1})
        refused = [
            client.get("/api/prices", params=query).status_code
            for query in ({}, {"drive_id": drive_id, "offer_id": first}, {"since": ago(1)})
        ]
    # Oldest first, each naming its offer.
    assert [p["item_price_cents"] for p in by_drive["items"]] == [20000, 19000, 18000, 17000]
    assert {p["offer_id"] for p in by_drive["items"]} == {first, other}
    assert by_drive["total"] == 4
    # A window holds every price in effect during it: the one still holding as it opens too.
    assert windowed == [19000, 18000, 17000]
    assert bounded == [20000, 19000]
    assert [p["item_price_cents"] for p in paged.json()["items"]] == [19000, 18000]
    assert paged.json()["total"] == 4
    assert refused == [422, 422, 422]


def test_offers_are_narrowed_to_a_drive_or_to_those_needing_a_check_by_hand(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        offers = catalogue(client)
        post(client, "/api/prices", scraped_payload(observed_at=ago(30)))
        drive_id = client.get(f"/api/offers/{offers['spd']}").json()["drive"]["id"]
        of_drive = client.get("/api/offers", params={"drive_id": drive_id}).json()
        overdue = client.get("/api/offers", params={"needs_recheck": True}).json()
        overdue_by_month = client.get(
            "/api/offers", params={"needs_recheck": True, "recent_days": 30}
        ).json()
    assert {offer["id"] for offer in of_drive} >= {offers["spd"], offers["shop"]}
    assert {offer["drive"]["id"] for offer in of_drive} == {drive_id}
    # Entered by hand and not checked within the recent window, longest unchecked first; a
    # collected offer is the collector's to check.
    assert [offer["id"] for offer in overdue] == [offers["stale"]]
    assert overdue_by_month == []


def test_what_drives_cost_today_is_reported_over_every_drive_in_stock(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offers = catalogue(client)
        marks = client.get("/api/reports/prices-today").json()
        ghd = client.get(f"/api/offers/{offers['ghd']}").json()
    # One mark for each drive in each condition it is in stock in, by item price per terabyte,
    # cheapest first; the cheapest checked recently is the lowest.
    assert [(mark["title"], mark["per_tb_cents"], mark["lowest"]) for mark in marks] == [
        ("Ultrastar HC520 12TB", 950, True),
        ("Exos X18 18TB", 1000, False),
        ("IronWolf 8TB", 2000, False),
    ]
    ghd_mark = next(mark for mark in marks if mark["title"] == "Ultrastar HC520 12TB")
    assert ghd_mark == {
        "drive_id": ghd["drive"]["id"],
        "condition": "manufacturer_recertified",
        "title": "Ultrastar HC520 12TB",
        "capacity_gb": 12000,
        "per_tb_cents": 950,
        "lowest": True,
    }


def test_offers_as_cheap_as_each_other_are_all_the_lowest_and_a_recheck_makes_one_recent(
    database_url: str,
) -> None:
    """Ties are kept; an offer checked recently counts, though its price is older."""
    with TestClient(create_app()) as client:
        first = record(client, seller="One", item_price_cents=18000, shipping_cents=0)
        second = record(client, seller="Two", item_price_cents=18000, shipping_cents=0)
        old = record(client, seller="Old", item_price_cents=17000, shipping_cents=0,
                     observed_at=ago(30))  # fmt: skip
        before = client.get("/api/drives").json()["lowest"]
        # Checked today at the price it has had for a month.
        record(client, seller="Old", item_price_cents=17000, shipping_cents=0)
        after = client.get("/api/drives").json()["lowest"]
    assert before == {"total": sorted([first, second]), "unit": sorted([first, second])}
    assert after == {"total": [old], "unit": [old]}


def test_a_drive_is_read_with_the_range_of_its_price_in_each_condition_over_the_days_asked_for(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        common = {"store": "goharddrive", "seller": "", "mpn": "ST16000NM001G",
                  "capacity_gb": 16000, "shipping_cents": 0}  # fmt: skip
        for days, cents in [(40, 20000), (10, 18000), (0.001, 18000)]:
            record(client, **common, condition="new", item_price_cents=cents, observed_at=ago(days))
        record(client, **common, condition="used", item_price_cents=9000, in_stock=False)
        offer_id = client.get("/api/offers").json()[0]["id"]
        drive_id = client.get(f"/api/offers/{offer_id}").json()["drive"]["id"]
        month = client.get(f"/api/drives/{drive_id}", params={"range_days": 30}).json()
        default = client.get(f"/api/drives/{drive_id}").json()
    # $200 held from the period's start until ten days ago, $180 since.
    assert month["ranges"] == {
        "new": {"today": 18000, "low": 18000, "high": 20000,
                "average": round((20000 * 20 + 18000 * 10) / 30), "days": 30},
        # Never in stock in the period: no range.
        "used": None,
    }  # fmt: skip
    # Ninety days unless asked: the offer is newer than that.
    assert default["ranges"]["new"]["days"] == 40


def catalog_mpns(page: dict[str, Any]) -> list[str]:
    return [row["drive"]["mpn"] for row in page["items"]]


def test_the_drives_to_manage_are_every_drive_a_page_at_a_time_with_what_each_needs(
    database_url: str,
) -> None:
    """Every drive, held offers and all, in stock first and cheapest terabyte first, each with
    how many offers it has and what it needs: specifications, or a check of an offer in stock
    not checked within recent_days. Each need is counted over every drive."""
    with TestClient(create_app()) as client:
        catalogue(client)
        first = client.get("/api/catalog-drives", params={"limit": 2}).json()
        second = client.get("/api/catalog-drives", params={"limit": 2, "offset": 2}).json()
        stale = client.get("/api/catalog-drives", params={"issue": "stale"}).json()
        later = client.get(
            "/api/catalog-drives", params={"issue": "stale", "recent_days": 30}
        ).json()
        refused = client.get("/api/catalog-drives", params={"issue": "broken"})

    assert catalog_mpns(first) + catalog_mpns(second) == [
        "WUH721212ALE6L4", "ST18000NM000J", "ST8000VN004", "ST14000NM001G",
    ]  # fmt: skip
    assert (first["total"], first["all"], first["limit"], first["offset"]) == (4, 4, 2, 0)
    assert first["items"][1] == {
        "drive": first["items"][1]["drive"],
        "title": "Exos X18 18TB",
        "offers": 2,
        "issues": ["unknown_specifications"],
    }
    assert [row["issues"] for row in second["items"]] == [
        ["unknown_specifications", "stale"], ["unknown_specifications"],
    ]  # fmt: skip
    assert first["issues"] == {"unknown_specifications": 3, "stale": 1}
    assert (catalog_mpns(stale), stale["total"], stale["all"]) == (["ST8000VN004"], 1, 4)
    assert later["total"] == 0
    assert refused.status_code == 422


def test_the_drives_to_manage_are_searched_by_every_name_with_a_drive_named_exactly_first(
    database_url: str,
) -> None:
    """By any name an offer of it goes by: its title, MPN, its drive's other MPNs, and who sells
    it. A drive the words are the MPN of, or another MPN of, comes first, so a form can tell a
    drive already recorded from those it only resembles."""
    with TestClient(create_app()) as client:
        catalogue(client)
        drives = {o["mpn"]: o["drive"]["id"] for o in client.get("/api/offers").json()}
        client.post(f"/api/drives/{drives['ST8000VN004']}/aliases", json={"mpn": "ST8000"})
        by_seller = client.get("/api/catalog-drives", params={"q": "old shop"}).json()
        by_title = client.get("/api/catalog-drives", params={"q": "exos"}).json()
        by_alias = client.get("/api/catalog-drives", params={"q": "st8000"}).json()
        exact = client.get("/api/catalog-drives", params={"q": "ST14000NM001G"}).json()
        resembling = client.get("/api/catalog-drives", params={"q": "ST1"}).json()

    assert catalog_mpns(by_seller) == ["ST8000VN004"]
    assert (catalog_mpns(by_title), by_title["all"]) == (["ST18000NM000J", "ST14000NM001G"], 4)
    # Its other MPN, and in ST8000VN004 itself.
    assert catalog_mpns(by_alias) == ["ST8000VN004"]
    assert catalog_mpns(exact) == ["ST14000NM001G"]
    assert catalog_mpns(resembling) == ["ST18000NM000J", "ST14000NM001G"]


def test_a_held_offer_is_still_a_drive_to_manage(database_url: str) -> None:
    with TestClient(create_app()) as client:
        page = scraped_payload(url="https://www.serverpartdeals.com/products/bundle", mpn="R0P90A",
                               title="HPE R0P90A 6TB", capacity_gb=6000, condition="refurbished")  # fmt: skip
        post(client, "/api/prices", page)
        post(client, "/api/prices", {**page, "title": "HPE R0P90A 48TB (8x6) 6-pack",
                                     "observed_at": ago(0.001)})  # fmt: skip
        listed = client.get("/api/drives").json()["total"]
        managed = client.get("/api/catalog-drives").json()

    assert (listed, catalog_mpns(managed)) == (0, ["R0P90A"])


def test_any_one_specification_known_is_specifications_enough(database_url: str) -> None:
    """Only a drive nothing is known of needs its specifications: a use it is meant for is one."""
    with TestClient(create_app()) as client:
        catalogue(client)
        drives = {o["mpn"]: o["drive"]["id"] for o in client.get("/api/offers").json()}
        client.patch(
            f"/api/drives/{drives['ST8000VN004']}",
            json={"specifications": {"intended_use": ["nas"]}},
        )
        needing = client.get(
            "/api/catalog-drives", params={"issue": "unknown_specifications"}
        ).json()

    assert catalog_mpns(needing) == ["ST18000NM000J", "ST14000NM001G"]


def test_how_fresh_each_stores_prices_are_is_reported_over_every_offer_it_has(
    database_url: str,
) -> None:
    """How many offers each store has, held ones and all, when the latest was checked, and when
    the middle one was (between the middle two, of an even number): stores with none are left
    out."""
    with TestClient(create_app()) as client:
        catalogue(client)
        record(
            client, seller="Shop two", mpn="ST12000NM001G", capacity_gb=12000, observed_at=ago(10)
        )
        report = client.get("/api/reports/store-freshness").json()

    at = {key: datetime.fromisoformat(value) for key, value in {
        "now": ago(0.01), "between": ago(5.005)}.items()}  # fmt: skip
    assert [
        (row["store"], row["offers"], datetime.fromisoformat(row["latest_checked_at"]),
         datetime.fromisoformat(row["median_checked_at"]))
        for row in report
    ] == [
        ("goharddrive", 1, at["now"], at["now"]),
        # Shop, the sold-out Exos X16, Old shop 20 days ago, Shop two 10 days ago.
        ("other", 4, at["now"], at["between"]),
        ("serverpartdeals", 1, at["now"], at["now"]),
    ]  # fmt: skip


def test_a_held_offer_is_in_no_price_range_though_it_and_its_prices_are_still_shown(
    database_url: str,
) -> None:
    """A drive at $200 from one store, and at $100 from another whose page has come to read as
    several drives: held, the $100 is no price of the drive's, on the prices page or its own
    page, while its offer and history stay there for a person to see."""
    with TestClient(create_app()) as client:
        eligible = record(client, seller="Shop", condition="new", item_price_cents=20000,
                          shipping_cents=0, observed_at=ago(0.01))  # fmt: skip
        page = scraped_payload(condition="new", item_price_cents=10000, observed_at=ago(0.02))
        held = post(client, "/api/prices", page).json()["offer_id"]
        post(
            client,
            "/api/prices",
            {**page, "title": f"{page['title']} 4-pack", "observed_at": ago(0.01)},
        )
        [row] = client.get("/api/drives", params={"range_days": 30}).json()["items"]
        detail = client.get(f"/api/drives/{row['drive']['id']}", params={"range_days": 30}).json()
        history = client.get("/api/prices", params={"offer_id": held}).json()

    # Priced minutes ago: no whole day of prices yet.
    only_eligible = {"today": 20000, "low": 20000, "high": 20000, "average": 20000, "days": 0}
    assert [offer["id"] for offer in row["offers"]] == [eligible]
    assert row["range"] == only_eligible
    assert detail["ranges"]["new"] == only_eligible
    assert sorted(offer["id"] for offer in detail["offers"]) == sorted([eligible, held])
    assert [price["item_price_cents"] for price in history["items"]] == [10000]
