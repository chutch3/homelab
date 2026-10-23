"""How the API uses the database: every read that takes several queries describes one moment,
every operation's writes are kept together or not at all, and no connection or transaction is
left behind. Changes made by someone else between a read's queries are made from a separate
connection, at the moment the read issues the query that would see them."""

import threading
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, suppress
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from api_calls import (
    entered,
    followed_drives,
    match,
    post,
    price_payload,
    scraped_payload,
    source_input,
)
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.exc import OperationalError

from disktracker.main import create_app


@contextmanager
def meanwhile(database_url: str, before: str, *changes: str, **values: Any) -> Iterator[list[str]]:
    """Commit changes, together, from another connection just before the first query containing
    before is sent by any other connection. Yields the statements they were made before."""
    elsewhere = create_engine(database_url)
    seen: list[str] = []

    def interrupt(connection: Any, cursor: Any, statement: str, *_: Any) -> None:
        if seen or before not in statement or connection.engine is elsewhere:
            return
        seen.append(statement)
        with elsewhere.begin() as other:
            for change in changes:
                other.execute(text(change), values)

    event.listen(Engine, "before_cursor_execute", interrupt)
    try:
        yield seen
    finally:
        event.remove(Engine, "before_cursor_execute", interrupt)
        elsewhere.dispose()


def run_sql(database_url: str, statement: str, **values: Any) -> list[Any]:
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            result = connection.execute(text(statement), values)
            return list(result) if result.returns_rows else []
    finally:
        engine.dispose()


def test_offers_listed_while_one_is_deleted_are_listed_as_they_all_were(
    database_url: str,
) -> None:
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        kept = post(client, "/api/prices", entered(client, price_payload(seller="Kept"))).json()[
            "offer_id"
        ]
        gone = post(client, "/api/prices", entered(client, price_payload(seller="Gone"))).json()[
            "offer_id"
        ]
        # Deleted after the offers are read, before their latest prices are.
        with meanwhile(
            database_url,
            "DISTINCT ON",
            "DELETE FROM observations WHERE listing_id = :id",
            "DELETE FROM listings WHERE id = :id",
            id=gone,
        ) as interrupted:
            listed = client.get("/api/offers")
        after = client.get("/api/offers").json()
    assert interrupted
    assert listed.status_code == 200, listed.text
    assert {offer["id"] for offer in listed.json()} == {kept, gone}
    assert [offer["id"] for offer in after] == [kept]


def test_a_drives_history_read_while_a_price_is_added_has_the_prices_its_offers_had(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        offer = post(client, "/api/prices", entered(client, price_payload())).json()["offer_id"]
        # Added after the offers' latest prices are read, before their histories are.
        with meanwhile(
            database_url,
            "ORDER BY observations.observed_at, observations.entered_at, observations.id",
            "INSERT INTO observations (id, listing_id, item_price_cents, shipping_cents, in_stock,"
            " observed_at, entered_at, notes, acquisition_method)"
            " VALUES (:price, :offer, 100, 0, true, now(), now(), '', 'manual')",
            price=uuid4(),
            offer=offer,
        ) as interrupted:
            history = client.get(f"/api/offers/{offer}").json()
    assert interrupted
    # Its latest price is the last of its history, as when it was read.
    assert [price["id"] for price in history["observations"]] == [history["latest"]["id"]]


def test_a_page_of_review_items_is_counted_with_the_items_it_was_read_from(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        for number in range(2):
            post(
                client,
                "/api/ingestions",
                scraped_payload(mpn=None, url=f"https://store.test/drive-{number}"),
            )
        # Queued after the queue is counted, before its items are read.
        with meanwhile(
            database_url,
            "LIMIT",
            "INSERT INTO unmatched (id, source, url, title, seller, in_stock, reason, provenance,"
            " first_seen_at, last_seen_at) VALUES (:id, 'serverpartdeals', 'https://store.test/x',"
            " 'X', '', true, 'missing_mpn', 'collected', now(), now())",
            id=uuid4(),
        ) as interrupted:
            page = client.get("/api/review-items", params={"limit": 50})
    assert interrupted
    assert page.headers["X-Total-Count"] == str(len(page.json())) == "2"


def test_a_trend_kept_while_a_price_is_recorded_is_what_working_it_out_afresh_gives(
    database_url: str,
) -> None:
    """A trend is kept under the revision of the very prices it was worked out from, so a price
    recorded while it is worked out is never taken for one it already has."""
    with TestClient(create_app()) as client:
        followed_drives(client, datetime.now(UTC))
        [offer] = [o["id"] for o in client.get("/api/offers").json() if o["mpn"] == "ST10000NM001G"]
        # Recorded while the trend's prices are being read.
        with meanwhile(
            database_url,
            "SELECT observations.listing_id, observations.observed_at",
            "INSERT INTO observations (id, listing_id, item_price_cents, shipping_cents, in_stock,"
            " observed_at, entered_at, notes, acquisition_method)"
            " VALUES (:price, :offer, 90000, 500, true, now(), now(), '', 'manual')",
            price=uuid4(),
            offer=offer,
        ) as interrupted:
            client.get("/api/trends", params={"days": 30})
        kept = client.get("/api/trends", params={"days": 30}).json()
        run_sql(database_url, "DELETE FROM trends")
        afresh = client.get("/api/trends", params={"days": 30}).json()
    assert interrupted
    assert kept == afresh


def test_deleting_a_source_is_undone_in_every_area_when_any_part_of_it_fails(
    database_url: str,
) -> None:
    """Forgetting what was decided about a source's offers (the catalog) and removing the source
    and its runs (collection) are one piece of work."""
    with TestClient(create_app(), raise_server_exceptions=False) as client:
        source = client.post("/api/sources", json=source_input())
        assert source.status_code == 201, source.text
        store, url = source.json()["key"], "https://orbit.test/p/1"
        queued = post(client, "/api/ingestions", scraped_payload(store=store, mpn=None, url=url))
        item = queued.json()["review_item_id"]
        client.put(f"/api/review-items/{item}/decision", json={"decision": "ignore"})
        run_sql(
            database_url,
            "CREATE FUNCTION refuse() RETURNS trigger AS $$ BEGIN RAISE EXCEPTION 'refused';"
            " END $$ LANGUAGE plpgsql; CREATE TRIGGER refuse BEFORE DELETE ON sources"
            " FOR EACH ROW EXECUTE FUNCTION refuse();",
        )
        failed = client.delete(f"/api/sources/{source.json()['id']}")
        later = post(client, "/api/ingestions", scraped_payload(store=store, mpn=None, url=url))
    decisions = run_sql(
        database_url, "SELECT ignored FROM scraped_matches WHERE source = :store", store=store
    )
    assert failed.status_code == 500
    # What was decided is still remembered: the offer is still ignored.
    assert [tuple(row) for row in decisions] == [(True,)]
    assert later.json()["status"] == "ignored"


def test_the_same_review_decision_sent_twice_at_once_records_one_price(database_url: str) -> None:
    with TestClient(create_app()) as client:
        decision = match(client, "ST18000NM000J", "manufacturer_recertified", 18000)
        queued = post(client, "/api/ingestions", scraped_payload(mpn=None, condition=None))
        path = f"/api/review-items/{queued.json()['review_item_id']}/decision"
        with ThreadPoolExecutor(max_workers=2) as executor:
            answers = list(executor.map(lambda _: client.put(path, json=decision), range(2)))
        offer = client.get(f"/api/offers/{answers[0].json()['offer_id']}").json()
    assert [answer.status_code for answer in answers] == [200, 200]
    assert answers[0].json() == answers[1].json()
    assert len(offer["observations"]) == 1


def backends(database_url: str, state: str | None = None) -> int:
    """How many connections other than this one are open to the test's database, in a state
    when one is named."""
    [(count,)] = run_sql(
        database_url,
        "SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()"
        " AND pid <> pg_backend_pid() AND (CAST(:state AS text) IS NULL OR state = :state)",
        state=state,
    )
    return int(count)


def test_no_transaction_is_left_open_by_a_request_that_succeeds_or_fails(
    database_url: str,
) -> None:
    requests: list[Callable[[TestClient], Any]] = [
        lambda client: client.get("/api/offers"),
        lambda client: client.get("/api/review-items"),
        lambda client: client.get("/api/trends", params={"days": 30}),
        lambda client: post(client, "/api/prices", entered(client, price_payload())),
        lambda client: post(client, "/api/prices", entered(client, price_payload(store="nowhere"))),
        lambda client: client.delete(f"/api/prices/{uuid4()}"),
        lambda client: client.patch(f"/api/drives/{uuid4()}", json={"capacity_gb": 1000}),
    ]
    with TestClient(create_app()) as client:
        for request in requests:
            request(client)
        left_open = backends(database_url, "idle in transaction")
    assert left_open == 0


def test_the_database_connections_are_closed_when_the_application_stops(
    database_url: str,
) -> None:
    with TestClient(create_app()) as client:
        post(client, "/api/prices", entered(client, price_payload()))
        client.get("/api/offers")
        while_running = backends(database_url)
    assert while_running >= 1
    assert backends(database_url) == 0


LOCK = "pg_advisory_xact_lock"


@contextmanager
def crossing(
    assign: Callable[[str, Any], str | None], pauses: dict[str, Callable[[str, int], bool]]
) -> Iterator[None]:
    """Make two requests cross. Each is told apart by the first statement of its work (assign
    names it from the statement and its parameters), and waits for the other just before the
    statement its pause picks (given the statement and how many locks it has taken), so both
    hold what they took first. One blocked before reaching its pause never gets there: the other
    then waits no longer than a moment, and goes on."""
    barrier = threading.Barrier(len(pauses))
    seen: list[Any] = []

    def pause(connection: Any, cursor: Any, statement: str, parameters: Any, *_: Any) -> None:
        info = connection.info
        role = assign(statement, parameters)
        if role is not None:
            info.update(role=role, locks=0, paused=False)
            seen.append(info)
        if info.get("role") not in pauses or info["paused"]:
            return
        info["locks"] += LOCK in statement
        if pauses[info["role"]](statement, info["locks"]):
            info["paused"] = True
            with suppress(threading.BrokenBarrierError):
                barrier.wait(timeout=2)

    event.listen(Engine, "before_cursor_execute", pause)
    try:
        yield
    finally:
        event.remove(Engine, "before_cursor_execute", pause)
        for info in seen:
            info.pop("role", None)


def test_two_pages_naming_each_others_mpns_at_once_are_both_taken(database_url: str) -> None:
    """Each a new drive naming the other's MPN as another of its own: whichever is taken first,
    the other is of the same drive. Neither waits for the other forever."""
    page = scraped_payload(capacity_gb=16000, title="Exos 16TB", condition="new")
    first = {
        **page,
        "url": "https://www.serverpartdeals.com/products/a",
        "mpn": "AAA1",
        "aliases": ["BBB1"],
    }
    second = {
        **page,
        "url": "https://www.serverpartdeals.com/products/b",
        "mpn": "BBB1",
        "aliases": ["AAA1"],
    }
    keys = {"a": uuid4(), "b": uuid4()}

    def assign(statement: str, parameters: Any) -> str | None:
        if not statement.startswith("INSERT INTO save_receipts"):
            return None
        return next((role for role, key in keys.items() if key in parameters.values()), None)

    # Each waits for the other once it holds its first lock and asks for its second.
    second_lock = {
        role: (lambda statement, locks: LOCK in statement and locks == 2) for role in keys
    }
    with (
        TestClient(create_app()) as client,
        crossing(assign, second_lock),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        answers = [
            executor.submit(post, client, "/api/ingestions", body, str(keys[role]))
            for role, body in (("a", first), ("b", second))
        ]
        results = [answer.result() for answer in answers]
    with TestClient(create_app()) as client:
        drives = {o["drive"]["id"] for o in client.get("/api/offers").json()}

    assert [result.status_code for result in results] == [201, 201], [r.text for r in results]
    assert len(drives) == 1


def test_a_review_decision_and_a_page_collected_again_at_once_both_finish(
    database_url: str,
) -> None:
    """The reviewer decides a listing as its page is collected again, read as doubtfully as
    before: one waits for the other, and neither forever."""
    page = scraped_payload(title="Seagate Exos X18 ST18000NM000J 18TB 4-pack")
    pauses = {
        # The reviewer, once it has its decision, as it asks for the drive's MPN.
        "review": lambda statement, locks: LOCK in statement and locks == 1,
        # The collector, once it holds the drive's MPN, as it keeps the item again.
        "collect": lambda statement, locks: statement.startswith("INSERT INTO unmatched"),
    }
    with TestClient(create_app()) as client:
        decision = match(client, "ST18000NM000J", "manufacturer_recertified", 18000)
        item = post(client, "/api/ingestions", page).json()["review_item_id"]
        decide = lambda: client.put(f"/api/review-items/{item}/decision", json=decision)
        collect = lambda: post(
            client, "/api/ingestions", {**page, "observed_at": "2026-09-22T12:00:00Z"}
        )
        roles = {"INSERT INTO review_decisions": "review", "INSERT INTO save_receipts": "collect"}

        def assign(statement: str, parameters: Any) -> str | None:
            return next(
                (role for start, role in roles.items() if statement.startswith(start)), None
            )

        with crossing(assign, pauses), ThreadPoolExecutor(max_workers=2) as executor:
            answers = [executor.submit(decide), executor.submit(collect)]
            results = [answer.result() for answer in answers]

    assert [result.status_code for result in results] == [200, 202], [r.text for r in results]


def test_a_drive_corrected_as_a_page_of_it_is_taken_in_never_takes_a_price_it_contradicts(
    database_url: str,
) -> None:
    """The page says 18 TB of a drive recorded at 18 TB; a person corrects the drive to 20 TB
    the moment before taking it in holds the drive. Whichever goes first, the page is never
    recorded as a drive of a capacity it contradicts: taken in as 18 TB before the correction,
    or waiting for review after it."""
    elsewhere = create_engine(database_url)
    corrected: list[bool] = []

    def correct(connection: Any, cursor: Any, statement: str, *_: Any) -> None:
        locking_drive = "FROM drives" in statement and "FOR UPDATE" in statement
        if corrected or not locking_drive or connection.engine is elsewhere:
            return
        try:
            with elsewhere.begin() as other:
                # Waiting no longer than a moment for a drive another operation holds.
                other.execute(text("SET LOCAL lock_timeout = '500ms'"))
                other.execute(
                    text("UPDATE drives SET capacity_gb = 20000 WHERE mpn = 'ST18000NM000J'")
                )
            corrected.append(True)
        except OperationalError:
            corrected.append(False)

    with TestClient(create_app()) as client:
        post(client, "/api/drives", {"mpn": "ST18000NM000J", "capacity_gb": 18000})
        event.listen(Engine, "before_cursor_execute", correct)
        try:
            taken = post(client, "/api/ingestions", scraped_payload())
        finally:
            event.remove(Engine, "before_cursor_execute", correct)
        [capacity] = run_sql(database_url, "SELECT capacity_gb FROM drives")
    elsewhere.dispose()

    assert taken.status_code in (201, 202), taken.text
    if corrected == [True]:
        # The correction came first: the page contradicts the drive.
        assert (taken.json()["status"], capacity[0]) == ("queued", 20000)
    else:
        assert (taken.json()["status"], capacity[0]) == ("recorded", 18000)
