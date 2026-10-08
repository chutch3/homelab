#!/usr/bin/env python3
"""Remove a store's offers from the Review queue that have been recorded since they were queued.

Before the backend's fix, an offer queued for review stayed there after a later run read it
well enough to record it (once the collector learned to read the store's model numbers, say),
so the queue kept asking for details the offer already had. This removes those queued offers;
the recorded offers and their prices are left as they are.

It only counts, and changes nothing, unless APPLY=1.

Usage, where the backend runs (it has the database's address and SQLAlchemy):
    docker exec -i -e STORE=serverorbit <backend container> python - < remove-recorded-from-review.py
    docker exec -i -e STORE=serverorbit -e APPLY=1 <backend container> python - < remove-recorded-from-review.py
"""

import os

from sqlalchemy import create_engine, text

STORE = os.environ["STORE"]
APPLY = os.environ.get("APPLY") == "1"

engine = create_engine(os.environ["DISKTRACKER_DATABASE_URL"])
with engine.connect() as connection:
    removed = connection.execute(
        text(
            "DELETE FROM unmatched WHERE source = :store AND EXISTS ("
            "SELECT 1 FROM listings WHERE listings.store = unmatched.source"
            " AND listings.url = unmatched.url)"
        ),
        {"store": STORE},
    ).rowcount
    remaining = connection.execute(
        text("SELECT count(*) FROM unmatched WHERE source = :store"), {"store": STORE}
    ).scalar_one()
    if APPLY:
        connection.commit()
    else:
        connection.rollback()

print(
    f"{STORE}: {'removed' if APPLY else 'would remove'} {removed} queued for review;"
    f" {remaining} {'remain' if APPLY else 'would remain'} queued."
)
if not APPLY:
    print("Nothing was changed. Run again with APPLY=1 to remove them.")
