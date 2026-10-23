"""Price trends: what they follow, and when a kept trend is answered or worked out again."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from api_calls import followed_drives, priced_days_ago, with_history
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from disktracker.main import create_app


def test_trends_follow_the_typical_item_price_per_terabyte_of_drives_priced_all_period(
    database_url: str,
) -> None:
    now = datetime.now(UTC)
    with TestClient(create_app()) as client:
        record = priced_days_ago(client, now)
        record("ST10000NM001G", 10000, 40.5)
        record("ST10000NM002G", 20000, 40.5)
        record("ST10000NM003G", 30000, 40.5)
        # Ten days ago the middle drive drops from $20 to $16 a terabyte.
        record("ST10000NM002G", 16000, 10.5)
        # A drive first priced five days ago is not counted: it would move the line by arriving.
        record("ST10000NM004G", 1000, 5.5)
        # Every offer was checked just now, so each price still stands.
        for mpn, item in [("ST10000NM001G", 10000), ("ST10000NM002G", 16000)]:
            record(mpn, item, 0.001)
        record("ST10000NM003G", 30000, 0.001)
        record("ST10000NM004G", 1000, 0.001)

        response = client.get("/api/trends", params={"days": 30})

    assert response.status_code == 200, response.text
    trends = response.json()
    assert (trends["days"], trends["by"], trends["parts"]) == (30, None, [])
    market = trends["market"]
    assert (market["counted"], market["of"]) == (3, 4)
    points = {point["days_ago"]: point for point in market["points"]}
    assert sorted(points) == list(range(31))
    # Cents per terabyte: the median drive, and the middle half around it. Shipping is left out.
    assert points[30] == {"days_ago": 30, "median": 2000, "low": 1500, "high": 2500}
    assert points[11] == {"days_ago": 11, "median": 2000, "low": 1500, "high": 2500}
    assert points[10] == {"days_ago": 10, "median": 1600, "low": 1300, "high": 2300}
    assert points[0] == {"days_ago": 0, "median": 1600, "low": 1300, "high": 2300}


def test_trends_split_the_market_when_asked_and_refuse_a_period_or_split_there_is_not(
    database_url: str,
) -> None:
    now = datetime.now(UTC)
    with TestClient(create_app()) as client:
        record = priced_days_ago(client, now)
        record("ST10000NM001G", 10000, 40.5)
        record("ST18000NM000J", 36000, 40.5, capacity_gb=18000)
        # Last checked ten days ago: within the fortnight asked for below, not within a week.
        record("ST10000NM001G", 10000, 10.5)
        record("ST18000NM000J", 36000, 0.001, capacity_gb=18000)

        split = {"days": 30, "by": "capacity"}
        by_capacity = client.get("/api/trends", params={**split, "recent_days": 14})
        strict = client.get("/api/trends", params=split)
        # Ninety days unless told otherwise.
        assert client.get("/api/trends").json()["days"] == 90
        assert client.get("/api/trends", params={"days": 45}).status_code == 422
        assert client.get("/api/trends", params={"by": "brand"}).status_code == 422
        assert client.get("/api/trends", params={"recent_days": 0}).status_code == 422

    assert by_capacity.status_code == 200, by_capacity.text
    trends = by_capacity.json()
    assert (trends["days"], trends["by"]) == (30, "capacity")
    assert [part["key"] for part in trends["parts"]] == ["10000", "18000"]
    small, large = (part["series"] for part in trends["parts"])
    assert small["points"][-1] == {"days_ago": 0, "median": 1000, "low": 1000, "high": 1000}
    assert large["points"][-1] == {"days_ago": 0, "median": 2000, "low": 2000, "high": 2000}
    # Left to the usual week, the offer unchecked for ten days ended at its last check.
    assert [point["days_ago"] for point in strict.json()["parts"][0]["series"]["points"]] == list(
        range(30, 10, -1)
    )


def test_a_trend_can_look_back_a_week_or_a_fortnight_and_says_how_far_back_prices_go(
    database_url: str,
) -> None:
    """Prices have been collected for ten days: a fortnight is too long to follow any drive
    over, a week is not."""
    now = datetime.now(UTC)
    with TestClient(create_app()) as client:
        record = priced_days_ago(client, now)
        first = now - timedelta(days=10)
        record("ST10000NM001G", 10000, 10)
        record("ST10000NM001G", 10000, 0.001)
        week = client.get("/api/trends", params={"days": 7}).json()
        fortnight = client.get("/api/trends", params={"days": 14}).json()

    assert (week["days"], week["market"]["counted"]) == (7, 1)
    assert (fortnight["days"], fortnight["market"]["counted"]) == (14, 0)
    for trend in (week, fortnight):
        since = datetime.fromisoformat(trend["since"])
        assert abs(since - first) < timedelta(minutes=1)


def test_a_trend_and_todays_prices_follow_only_the_drives_the_prices_page_would_show(
    database_url: str,
) -> None:
    """Narrowed by the same filters as the drives listed, each narrowing kept apart from the
    rest, so are the drives being considered getting cheaper is answered for them alone."""
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        for days in (40.5, 0.001):
            record("ST18000NM000J", 36000, days, capacity_gb=18000)
        every = client.get("/api/trends", params={"days": 30}).json()
        large = client.get("/api/trends", params={"days": 30, "capacity": 18000}).json()
        searched = client.get("/api/trends", params={"days": 30, "q": "ST10000NM00"}).json()
        again = client.get("/api/trends", params={"days": 30}).json()
        today = client.get("/api/reports/prices-today", params={"capacity": 18000}).json()
        refused = client.get("/api/trends", params={"days": 30, "limit": 5})

    assert (every["market"]["counted"], large["market"]["counted"]) == (4, 1)
    assert large["market"]["points"][-1]["median"] == 2000
    assert searched["market"]["counted"] == 3
    assert again == every
    assert [mark["capacity_gb"] for mark in today] == [18000]
    # Paging and order are the list's own.
    assert refused.status_code == 422


def test_trends_are_kept_once_worked_out_and_answered_from_what_was_kept(database_url: str) -> None:
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        followed_drives(client, datetime.now(UTC))
        first = client.get("/api/trends", params={"days": 30}).json()
        assert first["market"]["counted"] == 3
        with engine.begin() as connection:
            kept = connection.execute(text("SELECT days, by, recent_days FROM trends")).all()
            # Nothing but the kept answer says 99, so answering 99 is answering from it.
            connection.execute(
                text("UPDATE trends SET body = jsonb_set(body, '{market,counted}', '99')")
            )
        again = client.get("/api/trends", params={"days": 30}).json()
        client.get("/api/trends", params={"days": 30, "by": "capacity"})
        client.get("/api/trends", params={"days": 30, "recent_days": 14})
        with engine.connect() as connection:
            answers = connection.execute(text("SELECT count(*) FROM trends")).scalar_one()
    engine.dispose()

    assert kept == [(30, "", 7)]
    assert again == {**first, "market": {**first["market"], "counted": 99}}
    # One answer for each period, split and allowance asked for.
    assert answers == 3


def test_a_price_recorded_for_an_earlier_day_changes_that_day_of_a_kept_trend(
    database_url: str,
) -> None:
    """Prices can be entered backdated: one recorded now for ten days ago changes the trend from
    ten days ago on, though it was kept before."""
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        client.get("/api/trends", params={"days": 30})
        # The cheapest drive, at half its price ten days ago.
        record("ST10000NM001G", 5000, 10)
        kept = client.get("/api/trends", params={"days": 30}).json()
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM trends"))
        afresh = client.get("/api/trends", params={"days": 30}).json()
    engine.dispose()

    assert kept == afresh
    assert [point["low"] for point in afresh["market"]["points"] if point["days_ago"] == 9] != [
        1500
    ]


def test_a_price_recorded_since_a_trend_was_kept_has_it_worked_out_again(
    database_url: str,
) -> None:
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        first = client.get("/api/trends", params={"days": 30}).json()
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE trends SET body = jsonb_set(body, '{market,counted}', '99')")
            )
        # The middle drive drops from $20 to $16 a terabyte, and a drive is priced for the first time.
        record("ST10000NM002G", 16000, 0)
        record("ST10000NM004G", 1000, 0)
        after = client.get("/api/trends", params={"days": 30}).json()
    engine.dispose()

    assert first["market"]["points"][-1] == {
        "days_ago": 0,
        "median": 2000,
        "low": 1500,
        "high": 2500,
    }
    # Today is read again from the prices as they now stand, over the drives followed all period.
    assert after["market"]["points"][-1] == {
        "days_ago": 0,
        "median": 1600,
        "low": 1300,
        "high": 2300,
    }
    assert after["market"]["points"][:-1] == first["market"]["points"][:-1]
    # Worked out again, all of it: not the answer that was kept. The new drive was not priced
    # as the period opened, so it is not followed.
    assert (after["market"]["counted"], after["market"]["of"]) == (3, 4)


def test_a_trend_kept_on_an_earlier_day_is_worked_out_afresh_and_kept_again(
    database_url: str,
) -> None:
    """When a kept trend is answered is the service's (tests/unit/reporting/test_service.py);
    this is the day it was kept on, as the database has it."""
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        followed_drives(client, datetime.now(UTC))
        first = client.get("/api/trends", params={"days": 30}).json()
        with engine.begin() as connection:
            # As if it had been worked out yesterday; 99 is what only the kept answer says.
            connection.execute(
                text(
                    "UPDATE trends SET as_of = as_of - interval '1 day', "
                    "body = jsonb_set(body, '{market,counted}', '99')"
                )
            )
        after = client.get("/api/trends", params={"days": 30}).json()
        with engine.connect() as connection:
            kept_on = connection.execute(text("SELECT as_of::date FROM trends")).scalar_one()
    engine.dispose()

    assert after == first
    assert kept_on == datetime.now(UTC).date()


def kept_trend_poisoned(engine: Any) -> None:
    """Mark every kept trend, so that an answer carrying the mark was read from what was kept."""
    with engine.begin() as connection:
        connection.execute(
            text("UPDATE trends SET body = jsonb_set(body, '{market,counted}', '99')")
        )


def test_a_kept_trend_of_some_drives_is_worked_out_again_once_what_narrows_them_changes(
    database_url: str,
) -> None:
    """A trend of the drives a page narrows to reads what narrows them: a drive's brand and
    specifications, and the names search reads, an offer's title, its drive's other MPNs and the
    store's name. Changing any of them changes which drives it is of, though no price changed."""
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        followed_drives(client, datetime.now(UTC))
        offers = {o["mpn"]: o for o in client.get("/api/offers").json()}
        drive = offers["ST10000NM001G"]["drive"]["id"]
        [store] = [s for s in client.get("/api/sources").json() if s["key"] == "serverpartdeals"]
        entered = {k: v for k, v in store.items() if k not in ("id", "key", "next_run_at")}

        def counted_after(change: Any, **scope: Any) -> int:
            client.get("/api/trends", params={"days": 30, **scope})
            kept_trend_poisoned(engine)
            assert change().status_code in (200, 201)
            answer = client.get("/api/trends", params={"days": 30, **scope}).json()
            return int(answer["market"]["counted"])

        counts = {
            "brand": counted_after(
                lambda: client.patch(f"/api/drives/{drive}", json={"brand": "Exabyte"}),
                brand="Exabyte",
            ),
            "specification": counted_after(
                lambda: client.patch(
                    f"/api/drives/{drive}", json={"specifications": {"interface": "usb"}}
                ),
                interface="usb",
            ),
            "alias": counted_after(
                lambda: client.post(f"/api/drives/{drive}/aliases", json={"mpn": "XYZALIAS1"}),
                q="XYZALIAS1",
            ),
            "title": counted_after(
                lambda: client.patch(
                    f"/api/offers/{offers['ST10000NM002G']['id']}", json={"title": "Quillfeather"}
                ),
                q="Quillfeather",
            ),
            "store name": counted_after(
                lambda: client.put(
                    f"/api/sources/{store['id']}", json={**entered, "name": "Partorama"}
                ),
                q="Partorama",
            ),
        }
    engine.dispose()

    assert counts == {"brand": 1, "specification": 1, "alias": 1, "title": 1, "store name": 3}


def test_a_kept_trend_is_worked_out_again_once_a_drive_or_what_it_is_changes(
    database_url: str,
) -> None:
    """Trends group offers by drive and divide by its capacity, so correcting either changes
    them, though no price changed."""
    engine = create_engine(database_url)
    with TestClient(create_app()) as client:
        record = followed_drives(client, datetime.now(UTC))
        for days in (40.5, 0.001):
            record("ST10000NM004G", 40000, days, store="goharddrive")
        first = client.get("/api/trends", params={"days": 30}).json()
        drives = {o["mpn"]: o["drive"]["id"] for o in client.get("/api/offers").json()}

        kept_trend_poisoned(engine)
        resized = client.patch(f"/api/drives/{drives['ST10000NM001G']}", json={"capacity_gb": 5000})
        after_capacity = client.get("/api/trends", params={"days": 30}).json()

        kept_trend_poisoned(engine)
        # Its only offer is at a store the drive it joins has none at, so the offer moves whole.
        merged = client.post(
            f"/api/drives/{drives['ST10000NM004G']}/merge",
            json={"target_drive_id": drives["ST10000NM003G"]},
            headers={"Idempotency-Key": str(uuid4())},
        )
        after_merge = client.get("/api/trends", params={"days": 30}).json()

        kept_trend_poisoned(engine)
        # Without its price from before the period opened, a drive was not priced all period.
        offer = next(o for o in with_history(client) if o["mpn"] == "ST10000NM002G")
        deleted = client.delete(f"/api/prices/{offer['observations'][0]['id']}")
        after_deletion = client.get("/api/trends", params={"days": 30}).json()
    engine.dispose()
    assert (resized.status_code, merged.status_code) == (200, 200)
    assert first["market"]["counted"] == 4
    assert after_capacity["market"]["counted"] == 4
    assert after_capacity["market"]["points"] != first["market"]["points"]
    # Two offers of one drive in one condition are one item, counted once.
    assert after_merge["market"]["counted"] == 3
    assert (deleted.status_code, after_deletion["market"]["counted"]) == (204, 2)
