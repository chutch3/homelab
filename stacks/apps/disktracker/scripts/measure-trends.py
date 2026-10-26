#!/usr/bin/env python3
"""How long working out a trend takes on the data it is run against, without the kept trends:
reading the price changes of the drives in scope, and working the trend out of them, timed apart
for every drive and a few narrower scopes, over each period and split.

It only reads: everything is read in one read-only transaction, which is rolled back.

Usage, where the backend runs (it has the database's address and the backend's code):
    docker exec -i <backend container> python - < measure-trends.py
    docker exec -i -e RUNS=1 <backend container> python - < measure-trends.py   (each timing once)
"""

import os
import statistics
import time
from datetime import UTC, datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from disktracker.catalog.schemas import DriveScope
from disktracker.reporting.repository import _price_changes
from disktracker.reporting.trends import trends

RUNS = int(os.environ.get("RUNS", "3"))
PERIODS = (30, 90, 180)
SPLITS = (None, "condition", "capacity", "store")
RECENT_DAYS = 7


def timed(work):
    """The median of RUNS runs, in seconds, and what the last returned."""
    seconds = []
    for _ in range(RUNS):
        started = time.perf_counter()
        result = work()
        seconds.append(time.perf_counter() - started)
    return statistics.median(seconds), result


engine = create_engine(
    os.environ["DISKTRACKER_DATABASE_URL"],
    connect_args={"options": "-c timezone=UTC"},
    execution_options={"isolation_level": "REPEATABLE READ", "postgresql_readonly": True},
)
with Session(engine) as session:
    try:
        size = session.execute(
            text(
                "SELECT (SELECT count(*) FROM listings), (SELECT count(*) FROM observations),"
                " (SELECT count(*) FROM drives)"
            )
        ).one()
        print(f"offers {size[0]}, prices {size[1]}, drives {size[2]}\n")

        capacity, store = session.execute(
            text(
                "SELECT (SELECT d.capacity_gb FROM listings l JOIN drives d ON d.id = l.drive_id"
                "  GROUP BY 1 ORDER BY count(*) DESC LIMIT 1),"
                " (SELECT store FROM listings GROUP BY 1 ORDER BY count(*) DESC LIMIT 1)"
            )
        ).one()
        scopes = {
            "every drive": DriveScope(),
            "new": DriveScope(condition=["new"]),
            "search 'exos'": DriveScope(q="exos"),
        }
        # The capacity and the store with the most offers, when there are any.
        if capacity is not None:
            scopes[f"{capacity} GB"] = DriveScope(capacity=[capacity])
        if store is not None:
            scopes[f"store {store}"] = DriveScope(store=[store])

        for name, scope in scopes.items():
            read, offers = timed(lambda scope=scope: _price_changes(session, scope))
            changes = sum(len(offer.changes) for offer in offers)
            print(f"{name}: {len(offers)} offers, {changes} changes, read in {read:.3f}s")
            now = datetime.now(UTC)
            for days in PERIODS:
                worked = [
                    timed(lambda by=by: trends(offers, now, days, RECENT_DAYS, by))[0]  # noqa: B023
                    for by in SPLITS
                ]
                print(
                    f"  {days:>3} days: "
                    + ", ".join(f"{by or 'market'} {s:.3f}s" for by, s in zip(SPLITS, worked))
                )
    finally:
        session.rollback()
