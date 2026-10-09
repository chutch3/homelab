"""The scripts that put right what earlier collector faults recorded: each run as it is run in
production, as a script handed to Python with the database's address, against a database
holding the faulty records and others that must be left alone."""

import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, create_engine, insert, select

from disktracker.storage import drives, listings, mpn_aliases, observations, unmatched
from disktracker.web import create_app

SCRIPTS = Path(__file__).parents[3] / "scripts"
NOW = datetime(2026, 10, 2, 12, tzinfo=UTC)
BASE = "https://serverorbit.com/"
UNCHANGED = "Nothing was changed. Run again with APPLY=1 to remove them."


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
    with TestClient(create_app(database_url)) as client:
        for name in ("ServerOrbit", "Elsewhere"):
            added = client.post(
                "/api/sources", json={"name": name, "kind": "sitemap", "base_url": BASE}
            )
            assert added.status_code == 201, added.text
    return database_url


def offer(
    db: Connection, store: str, mpn: str, url: str, prices: list[int], alias: str | None = None
) -> None:
    """An offer of the drive with this MPN (made if no other offer has), at these prices."""
    drive = db.execute(select(drives.c.id).where(drives.c.mpn == mpn)).scalar()
    if drive is None:
        drive = uuid4()
        db.execute(insert(drives).values(id=drive, mpn=mpn, capacity_gb=16000))
    if alias:
        db.execute(insert(mpn_aliases).values(alias=alias, drive_id=drive))
    listing = uuid4()
    db.execute(
        insert(listings).values(
            id=listing,
            title="Drive",
            mpn=mpn,
            store=store,
            seller="",
            url=url,
            condition="new",
            drive_id=drive,
        )
    )
    for price in prices:
        db.execute(
            insert(observations).values(
                id=uuid4(),
                listing_id=listing,
                item_price_cents=price,
                shipping_cents=0,
                in_stock=True,
                observed_at=NOW,
                entered_at=NOW,
                notes="",
            )
        )


def queued(db: Connection, url: str, mpn: str | None, price: int) -> None:
    db.execute(
        insert(unmatched).values(
            id=uuid4(),
            source="serverorbit",
            url=url,
            title="Drive",
            seller="",
            mpn=mpn,
            item_price_cents=price,
            in_stock=True,
            reason="missing_condition",
            first_seen_at=NOW,
            last_seen_at=NOW,
        )
    )


def left(database_url: str) -> dict[str, list[object]]:
    """What the database holds: offers by store and MPN, drives, prices, queued offers, aliases."""
    engine = create_engine(database_url)
    with engine.connect() as db:
        found = {
            "offers": sorted(db.execute(select(listings.c.store, listings.c.mpn)).tuples()),
            "drives": sorted(db.execute(select(drives.c.mpn)).scalars()),
            "prices": sorted(db.execute(select(observations.c.item_price_cents)).scalars()),
            "queued": sorted(db.execute(select(unmatched.c.url)).scalars()),
            "aliases": sorted(db.execute(select(mpn_aliases.c.alias)).scalars()),
        }
    engine.dispose()
    return found


class TestRemoveUrlModelNumbers:
    """Offers recorded under a model number made from their page's address."""

    @pytest.fixture
    def faulty(self, database: str) -> str:
        engine = create_engine(database)
        with engine.begin() as db:
            # Alone under its made-up number: offer, price, drive and alias all go.
            offer(
                db,
                "serverorbit",
                "DELL-0HNHWC-16TB-SAS",
                f"{BASE}dell-0hnhwc-16tb-sas/",
                [100],
                alias="0HNHWC",
            )
            # Another store has an offer of the drive made for it: the drive stays.
            offer(db, "serverorbit", "HPE-P1-16TB", f"{BASE}hpe-p1-16tb/", [200])
            offer(db, "elsewhere", "HPE-P1-16TB", f"{BASE}hpe-p1-16tb/", [300])
            # A real model number, though its address ends otherwise: left alone.
            offer(db, "serverorbit", "HUH721010ALN600", f"{BASE}wd-huh721010aln600-10tb/", [400])
            queued(db, f"{BASE}emc-1-16tb/", "EMC-1-16TB", 500)
            queued(db, f"{BASE}real-queued/", "ST16000NM001G", 600)
        engine.dispose()
        return database

    def test_it_counts_and_changes_nothing_unless_told_to_apply(self, faulty: str) -> None:
        before = left(faulty)

        said = run("remove-url-model-numbers.py", faulty)

        counted = (
            "serverorbit: would remove 2 offers, 2 prices, 1 drives, 1 queued for review;"
            " 1 offers would remain."
        )
        assert said.splitlines() == [counted, UNCHANGED]
        assert left(faulty) == before

    def test_applied_it_removes_them_and_what_only_they_needed(self, faulty: str) -> None:
        said = run("remove-url-model-numbers.py", faulty, APPLY="1")

        assert said.strip() == (
            "serverorbit: removed 2 offers, 2 prices, 1 drives, 1 queued for review;"
            " 1 offers remain."
        )
        assert left(faulty) == {
            "offers": [("elsewhere", "HPE-P1-16TB"), ("serverorbit", "HUH721010ALN600")],
            "drives": ["HPE-P1-16TB", "HUH721010ALN600"],
            "prices": [300, 400],
            "queued": [f"{BASE}real-queued/"],
            "aliases": [],
        }


class TestRemoveZeroPrices:
    """Prices of $0.00, recorded for drives a store sells only by quote."""

    @pytest.fixture
    def faulty(self, database: str) -> str:
        engine = create_engine(database)
        with engine.begin() as db:
            # Never priced above nothing: offer and drive go with the price.
            offer(db, "serverorbit", "ZERO-ONLY", f"{BASE}a/", [0], alias="Z0")
            # The drive is another store's too: it stays.
            offer(db, "serverorbit", "ZERO-SHARED", f"{BASE}b/", [0])
            offer(db, "elsewhere", "ZERO-SHARED", f"{BASE}b/", [500])
            # Priced since: the offer keeps its real price.
            offer(db, "serverorbit", "ZERO-THEN-PRICED", f"{BASE}c/", [0, 900])
            # Another store's price of nothing is not this run's to remove.
            offer(db, "elsewhere", "ZERO-ELSEWHERE", f"{BASE}d/", [0])
            queued(db, f"{BASE}queued-at-nothing/", None, 0)
            queued(db, f"{BASE}queued-at-a-price/", None, 700)
        engine.dispose()
        return database

    def test_it_counts_and_changes_nothing_unless_told_to_apply(self, faulty: str) -> None:
        before = left(faulty)

        said = run("remove-zero-prices.py", faulty)

        counted = (
            "serverorbit: would remove 3 prices of $0.00, 2 offers left with no price,"
            " 1 drives left with no offer, 1 queued for review at $0.00; 1 offers would remain."
        )
        assert said.splitlines() == [counted, UNCHANGED]
        assert left(faulty) == before

    def test_applied_it_removes_them_and_what_only_they_needed(self, faulty: str) -> None:
        said = run("remove-zero-prices.py", faulty, APPLY="1")

        assert said.strip() == (
            "serverorbit: removed 3 prices of $0.00, 2 offers left with no price,"
            " 1 drives left with no offer, 1 queued for review at $0.00; 1 offers remain."
        )
        assert left(faulty) == {
            "offers": [
                ("elsewhere", "ZERO-ELSEWHERE"),
                ("elsewhere", "ZERO-SHARED"),
                ("serverorbit", "ZERO-THEN-PRICED"),
            ],
            "drives": ["ZERO-ELSEWHERE", "ZERO-SHARED", "ZERO-THEN-PRICED"],
            "prices": [0, 500, 900],
            "queued": [f"{BASE}queued-at-a-price/"],
            "aliases": [],
        }


class TestRemoveRecordedFromReview:
    """Offers left waiting in Review though a later run recorded them."""

    @pytest.fixture
    def faulty(self, database: str) -> str:
        engine = create_engine(database)
        with engine.begin() as db:
            # Recorded since it was queued: no longer waiting for anybody.
            offer(db, "serverorbit", "MZ7L31T9HBLT", f"{BASE}recorded/", [100])
            queued(db, f"{BASE}recorded/", None, 100)
            # Never recorded: still to be reviewed.
            queued(db, f"{BASE}waiting/", None, 200)
            # Recorded by another store only, at the same address: still to be reviewed.
            offer(db, "elsewhere", "ST16000NM001G", f"{BASE}elsewhere/", [300])
            queued(db, f"{BASE}elsewhere/", None, 300)
        engine.dispose()
        return database

    def test_it_counts_and_changes_nothing_unless_told_to_apply(self, faulty: str) -> None:
        before = left(faulty)

        said = run("remove-recorded-from-review.py", faulty)

        counted = "serverorbit: would remove 1 queued for review; 2 would remain queued."
        assert said.splitlines() == [counted, UNCHANGED]
        assert left(faulty) == before

    def test_applied_it_removes_them_and_leaves_the_offers(self, faulty: str) -> None:
        before = left(faulty)

        said = run("remove-recorded-from-review.py", faulty, APPLY="1")

        assert said.strip() == "serverorbit: removed 1 queued for review; 2 remain queued."
        assert left(faulty) == {
            **before,
            "queued": [f"{BASE}elsewhere/", f"{BASE}waiting/"],
        }
