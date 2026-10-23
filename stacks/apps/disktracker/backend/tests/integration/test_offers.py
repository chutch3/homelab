"""Offers as people read and correct them: listed, fetched with their history, edited and removed."""

from uuid import uuid4

from api_calls import entered, post, price_payload, saved_offer
from fastapi.testclient import TestClient

from disktracker.main import create_app


def test_missing_offer_returns_404(database_url: str) -> None:
    with TestClient(create_app()) as client:
        assert client.get(f"/api/offers/{uuid4()}").status_code == 404


def test_deleting_a_wrong_price_removes_it_and_deleting_the_last_price_removes_the_offer(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", entered(client, price_payload()))
        typo = saved_offer(
            client,
            post(
                client,
                "/api/prices",
                entered(
                    client, price_payload(item_price_cents=1890, observed_at="2026-09-22T12:00:00Z")
                ),
            ),
        )
        wrong, right = typo["observations"][1]["id"], typo["observations"][0]["id"]
        deleted = client.delete(f"/api/prices/{wrong}")
        kept = client.get(f"/api/offers/{typo['id']}").json()
        # A price already gone is gone: deleting it again, or one never kept, is no error.
        again = client.delete(f"/api/prices/{wrong}")
        never = client.delete(f"/api/prices/{uuid4()}")
        malformed = client.delete("/api/prices/not-a-price")
        last = client.delete(f"/api/prices/{right}")
        offers = client.get("/api/offers").json()
    assert (deleted.status_code, deleted.content) == (204, b"")
    assert [o["item_price_cents"] for o in kept["observations"]] == [18900]
    assert kept["latest"]["item_price_cents"] == 18900
    assert (again.status_code, never.status_code, malformed.status_code) == (204, 204, 422)
    # Its last price gone, the offer goes with it.
    assert (last.status_code, offers) == (204, [])


def test_deleting_an_offer_removes_it_and_its_prices(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offer = saved_offer(client, post(client, "/api/prices", entered(client, price_payload())))
        kept = saved_offer(
            client,
            post(client, "/api/prices", entered(client, price_payload(seller="Other seller"))),
        )
        assert client.delete(f"/api/offers/{offer['id']}").status_code == 204
        assert [o["id"] for o in client.get("/api/offers").json()] == [kept["id"]]
        assert client.delete(f"/api/offers/{offer['id']}").status_code == 404


def test_editing_an_offer_updates_its_details_in_place(database_url: str) -> None:
    with TestClient(create_app()) as client:
        offer = saved_offer(client, post(client, "/api/prices", entered(client, price_payload())))
        path = f"/api/offers/{offer['id']}"
        edited = client.patch(path, json={"title": "Exos X18 18TB", "url": None})
        assert edited.status_code == 200, edited.text
        assert edited.json()["title"] == "Exos X18 18TB"
        assert edited.json()["url"] is None
        assert client.get(path).json() == edited.json()
        addressed = client.patch(path, json={"url": "https://store.test/p/1"})
        assert (addressed.status_code, addressed.json()["url"]) == (200, "https://store.test/p/1")
        assert client.patch(path, json={"seller": "Someone else"}).status_code == 422
        assert client.patch(path, json={"capacity_gb": 20000}).status_code == 422
        assert client.patch(f"/api/offers/{uuid4()}", json={"title": "x"}).status_code == 404


def test_later_prices_never_overwrite_the_title_or_url_an_offer_was_created_with(
    database_url: str,
) -> None:
    untitled = price_payload()
    del untitled["title"]
    with TestClient(create_app()) as client:
        first = post(client, "/api/prices", entered(client, untitled))
        assert saved_offer(client, first)["title"] == "ST18000NM000J"
        client.patch(f"/api/offers/{first.json()['offer_id']}", json={"title": "Exos X18"})
        later = post(
            client,
            "/api/prices",
            entered(client, {**untitled, "observed_at": "2026-09-22T12:00:00Z"}),
        )
        assert saved_offer(client, later)["title"] == "Exos X18"
        retitled = post(
            client,
            "/api/prices",
            entered(client, price_payload(title="Scraped title", url="https://example.com/?ref=1")),
        )
        assert saved_offer(client, retitled)["title"] == "Exos X18"
        assert saved_offer(client, retitled)["url"] == "https://example.com/disk"


def test_listings_carry_each_offers_latest_price_and_history_is_fetched_per_offer(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        first = saved_offer(
            client, post(client, "/api/prices", entered(client, price_payload(seller="Shop A")))
        )
        post(
            client,
            "/api/prices",
            entered(
                client,
                price_payload(
                    seller="Shop A", item_price_cents=17900, observed_at="2026-09-22T12:00:00Z"
                ),
            ),
        )
        other = saved_offer(
            client, post(client, "/api/prices", entered(client, price_payload(seller="Shop B")))
        )
        post(client, "/api/prices", entered(client, price_payload(seller="Shop C")))

        summaries = client.get("/api/offers").json()
        histories = [client.get(f"/api/offers/{offer['id']}").json() for offer in (first, other)]

    assert all("observations" not in summary for summary in summaries)
    latest = {summary["seller"]: summary["latest"]["item_price_cents"] for summary in summaries}
    assert latest == {"Shop A": 17900, "Shop B": 18900, "Shop C": 18900}
    assert {
        history["seller"]: [o["item_price_cents"] for o in history["observations"]]
        for history in histories
    } == {"Shop A": [18900, 17900], "Shop B": [18900]}


def test_listings_can_be_narrowed_to_one_store(database_url: str) -> None:
    with TestClient(create_app()) as client:
        post(
            client,
            "/api/prices",
            entered(client, price_payload(store="serverpartdeals", seller="")),
        )
        post(client, "/api/prices", entered(client, price_payload(store="other", seller="Shop")))

        narrowed = client.get("/api/offers", params={"store": "serverpartdeals"}).json()
        everything = client.get("/api/offers").json()
        unknown = client.get("/api/offers", params={"store": "frys"})

    assert [listing["store"] for listing in narrowed] == ["serverpartdeals"]
    assert sorted(listing["store"] for listing in everything) == ["other", "serverpartdeals"]
    # Stores are data now: a store nothing is recorded under simply lists nothing.
    assert (unknown.status_code, unknown.json()) == (200, [])
