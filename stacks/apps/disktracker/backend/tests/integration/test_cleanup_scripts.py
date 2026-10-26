"""The script that holds offers collected before they would have been doubted, run as it is run
in production, as a script handed to Python with the database's address, against a database
holding those offers and others that must be left alone."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from api_calls import match
from fastapi.testclient import TestClient
from sqlalchemy import Connection, create_engine, insert, select

from disktracker.catalog.models import Drive, MpnAlias, Offer, Price, ReviewItem, ScrapedMatch
from disktracker.main import create_app

# The records are made and read by their tables, as the scripts, which run as SQL, see them.
drives, listings, mpn_aliases, observations, unmatched, scraped_matches = (
    model.__table__ for model in (Drive, Offer, MpnAlias, Price, ReviewItem, ScrapedMatch)
)

SCRIPTS = Path(__file__).parents[3] / "scripts"
NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)
BASE = "https://serverorbit.com/"


def run(script: str, database_url: str, **env: str) -> str:
    """What the script printed, run on the store serverorbit."""
    with (SCRIPTS / script).open() as source:
        done = subprocess.run(
            [sys.executable, "-"],
            stdin=source,
            capture_output=True,
            text=True,
            check=False,
            env={
                **os.environ,
                "DISKTRACKER_DATABASE_URL": database_url,
                "STORE": "serverorbit",
                **env,
            },
        )
    assert done.returncode == 0, done.stderr
    return done.stdout


@pytest.fixture
def database(database_url: str) -> str:
    """A database with the stores ServerOrbit and Elsewhere, both read from sitemaps."""
    with TestClient(create_app()) as client:
        for name in ("ServerOrbit", "Elsewhere"):
            added = client.post(
                "/api/sources", json={"name": name, "kind": "sitemap", "base_url": BASE}
            )
            assert added.status_code == 201, added.text
    return database_url


def queued(
    db: Connection, url: str, mpn: str | None, price: int, condition: str | None = None
) -> None:
    """A listing of serverorbit's waiting for review: for its condition, unless it gave one."""
    db.execute(
        insert(unmatched).values(
            id=uuid4(),
            source="serverorbit",
            url=url,
            title="Drive",
            seller="",
            mpn=mpn,
            condition=condition,
            item_price_cents=price,
            in_stock=True,
            reason="missing_condition" if condition is None else "implausible_capacity",
            provenance="collected",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
    )


def left(database_url: str) -> dict[str, list[object]]:
    """What the database holds: offers by store and MPN, drives, prices, queued offers, aliases."""
    engine = create_engine(database_url)
    with engine.connect() as db:
        found = {
            "offers": sorted(
                db.execute(
                    select(listings.c.store, drives.c.mpn).join(
                        drives, drives.c.id == listings.c.drive_id
                    )
                ).tuples()
            ),
            "drives": sorted(db.execute(select(drives.c.mpn)).scalars()),
            "prices": sorted(db.execute(select(observations.c.item_price_cents)).scalars()),
            "queued": sorted(db.execute(select(unmatched.c.url)).scalars()),
            "aliases": sorted(db.execute(select(mpn_aliases.c.alias)).scalars()),
        }
    engine.dispose()
    return found


# What the script says of the offers TestHoldDoubtedOffers records, before it is told to apply.
HOLD_REPORT = (
    "Would hold 3 offers while a person settles what their pages are:",
    (
        f"  {BASE}bundle: R0P90A, refurbished, 'HPE R0P90A 48TB (8x6) 6-pack': it may not be one"
        " drive. 1 price kept, 2026-10-02 to 2026-10-02; queued for review."
    ),
    (
        f"  {BASE}huge: KPM7XVUG960G, refurbished, 'Kioxia KPM7XVUG960G 960GB SAS': its capacity is"
        " more than any drive holds or other than its title says. 2 prices kept, 2026-10-02 to"
        " 2026-10-02; queued for review."
    ),
    (
        f"  {BASE}misread: P09094-H21, refurbished, 'HPE P09094-H213.2TB SAS 12GBPS Smart"
        " Carrier': its capacity is more than any drive holds or other than its title says."
        " 1 price kept, 2026-10-02 to 2026-10-02; already queued for review."
    ),
    (
        "Their prices are kept as they are. Held, an offer counts in no ranking, no prices today"
        " and no trend until a person says what its page is, or it is next collected without"
        " doubt."
    ),
    "Left as they are: 1 entered by hand, 1 settled by a person, 0 already held.",
)


class TestHoldDoubtedOffers:
    """Offers collected before their titles and capacities were doubted at collection, so still
    counted in rankings, today's prices and trends. Which are doubted is the catalog rules'
    (tests/unit/catalog/test_rules.py)."""

    @pytest.fixture
    def recorded(self, database: str) -> str:
        engine = create_engine(database)
        with engine.begin() as db:
            collected(db, "plain", "ST18000NM000J", "Seagate Exos X18 ST18000NM000J 18TB", 18000)
            # The store's 960TB, as it was read before.
            collected(db, "huge", "KPM7XVUG960G", "Kioxia KPM7XVUG960G 960GB SAS", 960000,
                      prices=[114000, 110000])  # fmt: skip
            collected(db, "bundle", "R0P90A", "HPE R0P90A 48TB (8x6) 6-pack", 6000)
            # Under any ceiling, but its own title says 3.2TB; already waiting for a person.
            collected(db, "misread", "P09094-H21", "HPE P09094-H213.2TB SAS 12GBPS Smart Carrier",
                      213200)  # fmt: skip
            queued(db, f"{BASE}misread", "P09094-H21", 7450, condition="refurbished")
            # As a person entered it.
            collected(db, "entered", "R0Q67A", "HPE R0Q67A 14.4TB (2.4TB x6)", 14400,
                      provenance="manual")  # fmt: skip
            # A person has said what its page is.
            collected(db, "settled", "Q2R41A", "HPE Q2R41A 2-pack", 4000)
            db.execute(
                insert(scraped_matches).values(
                    source="serverorbit", url=f"{BASE}settled",
                    drive_id=select(drives.c.id).where(drives.c.mpn == "Q2R41A").scalar_subquery(),
                    condition="refurbished", ignored=False,
                )
            )  # fmt: skip
        engine.dispose()
        return database

    def test_it_says_what_it_would_hold_and_why_and_changes_nothing(self, recorded: str) -> None:
        before = left(recorded), held(recorded)

        said = run("hold-doubted-offers.py", recorded)

        assert said.splitlines() == [
            *HOLD_REPORT,
            "Nothing was changed. Run again with APPLY=1 to hold them.",
        ]
        assert (left(recorded), held(recorded)) == before

    def test_applied_it_holds_them_keeping_their_prices_and_queues_their_pages(
        self, recorded: str
    ) -> None:
        before = left(recorded)

        said = run("hold-doubted-offers.py", recorded, APPLY="1")
        again = run("hold-doubted-offers.py", recorded, APPLY="1")

        assert said.splitlines() == [HOLD_REPORT[0].replace("Would hold", "Held"), *HOLD_REPORT[1:]]
        assert held(recorded) == {
            "R0P90A": "not_a_single_drive",
            "KPM7XVUG960G": "implausible_capacity",
            "P09094-H21": "implausible_capacity",
        }
        assert left(recorded) == {
            **before,
            "queued": sorted([f"{BASE}bundle", f"{BASE}huge", f"{BASE}misread"]),
        }
        # Run again, it finds them held and changes nothing.
        assert again.splitlines() == [
            "Held 0 offers while a person settles what their pages are.",
            "Left as they are: 1 entered by hand, 1 settled by a person, 3 already held.",
        ]

    def test_once_held_they_count_for_nothing_until_a_person_settles_them(
        self, recorded: str
    ) -> None:
        run("hold-doubted-offers.py", recorded, APPLY="1")
        with TestClient(create_app()) as client:
            # Recent enough to be ranked, all of them.
            asked = {"recent_days": 30}
            market = "/api/reports/market"
            counted = {r["drive"]["mpn"] for r in client.get(market, params=asked).json()["items"]}
            [item] = [
                i for i in client.get("/api/review-items").json() if i["url"] == f"{BASE}bundle"
            ]
            decided = client.put(
                f"/api/review-items/{item['id']}/decision",
                json=match(client, "R0P90A", "refurbished", 6000),
            )
            settled = {r["drive"]["mpn"] for r in client.get(market, params=asked).json()["items"]}

        assert counted == {"ST18000NM000J", "R0Q67A", "Q2R41A"}
        assert decided.status_code == 200, decided.text
        assert settled == counted | {"R0P90A"}
        assert held(recorded) == {
            "KPM7XVUG960G": "implausible_capacity",
            "P09094-H21": "implausible_capacity",
        }


def collected(
    db: Connection,
    page: str,
    mpn: str,
    title: str,
    capacity_gb: int,
    prices: list[int] | None = None,
    provenance: str = "collected",
) -> None:
    """An offer at serverorbit's page of that name, of a drive with this MPN and capacity, at
    these prices, as it was recorded."""
    drive = uuid4()
    db.execute(insert(drives).values(id=drive, mpn=mpn, capacity_gb=capacity_gb))
    listing = uuid4()
    db.execute(
        insert(listings).values(
            id=listing, title=title, store="serverorbit", seller="", url=BASE + page,
            condition="refurbished", drive_id=drive,
        )
    )  # fmt: skip
    for price in prices or [9000]:
        db.execute(
            insert(observations).values(
                id=uuid4(), listing_id=listing, item_price_cents=price, shipping_cents=0,
                in_stock=True, observed_at=NOW, entered_at=NOW, notes="",
                acquisition_method=provenance,
            )
        )  # fmt: skip


def held(database_url: str) -> dict[str, str]:
    """The offers held, by MPN, with why."""
    engine = create_engine(database_url)
    with engine.connect() as db:
        found = dict(
            db.execute(
                select(drives.c.mpn, listings.c.held_reason)
                .join(drives, drives.c.id == listings.c.drive_id)
                .where(listings.c.held_reason.is_not(None))
            )
            .tuples()
            .all()
        )
    engine.dispose()
    return found
