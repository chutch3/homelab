#!/usr/bin/env python3
"""Remove a store's offers that were recorded under a model number made from their page's URL.

Before the collector's fix, a sitemap source gave any drive whose maker it did not know the
last part of its page's path as its MPN ("DELL-0HNHWC-16TB-SAS-12GBPS-7200RPM-..."), which no
other store shares. This removes those offers with their prices, the drives that were created
for them and are left with no offer, and the queued offers waiting in Review under such a
number. The store's next run reads them again: with a real MPN where the title has one, else
into the Review queue.

It only counts, and changes nothing, unless APPLY=1.

Usage, where the backend runs (it has the database's address and SQLAlchemy):
    docker exec -i -e STORE=serverorbit <backend container> python - < remove-url-model-numbers.py
    docker exec -i -e STORE=serverorbit -e APPLY=1 <backend container> python - < remove-url-model-numbers.py
"""

import os

from sqlalchemy import create_engine, text

STORE = os.environ["STORE"]
APPLY = os.environ.get("APPLY") == "1"
# The last part of a page's path, in capitals: what the collector used for a model number.
FROM_URL = "upper(regexp_replace(regexp_replace(url, '/+$', ''), '^.*/', ''))"

engine = create_engine(os.environ["DISKTRACKER_DATABASE_URL"])
with engine.connect() as connection:
    connection.execute(
        text(
            "CREATE TEMPORARY TABLE mistaken ON COMMIT DROP AS"
            f" SELECT id, drive_id FROM listings WHERE store = :store AND mpn = {FROM_URL}"
        ),
        {"store": STORE},
    )
    counted = {
        "offers": connection.execute(text("SELECT count(*) FROM mistaken")).scalar_one(),
        "prices": connection.execute(
            text("DELETE FROM observations WHERE listing_id IN (SELECT id FROM mistaken)")
        ).rowcount,
    }
    connection.execute(text("DELETE FROM listings WHERE id IN (SELECT id FROM mistaken)"))
    # Drives made for those offers alone; one another offer still names is kept.
    orphaned = (
        "SELECT drive_id FROM mistaken"
        " WHERE NOT EXISTS (SELECT 1 FROM listings WHERE listings.drive_id = mistaken.drive_id)"
    )
    connection.execute(text(f"DELETE FROM mpn_aliases WHERE drive_id IN ({orphaned})"))
    counted["drives"] = connection.execute(
        text(f"DELETE FROM drives WHERE id IN ({orphaned})")
    ).rowcount
    counted["queued for review"] = connection.execute(
        text(f"DELETE FROM unmatched WHERE source = :store AND mpn = {FROM_URL}"),
        {"store": STORE},
    ).rowcount
    remaining = connection.execute(
        text("SELECT count(*) FROM listings WHERE store = :store"), {"store": STORE}
    ).scalar_one()
    if APPLY:
        connection.commit()
    else:
        connection.rollback()

print(f"{STORE}: {'removed' if APPLY else 'would remove'} " + ", ".join(
    f"{count} {name}" for name, count in counted.items()
) + f"; {remaining} offers {'remain' if APPLY else 'would remain'}.")
if not APPLY:
    print("Nothing was changed. Run again with APPLY=1 to remove them.")
