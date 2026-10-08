#!/usr/bin/env python3
"""Remove a store's prices of $0.00, which are not prices.

Before the collector's fix, a sitemap source recorded a drive its page priced at 0 (a store's
way of writing "sold by quote") as on offer for nothing, which then showed as the lowest price
of everything. This removes those prices, the offers left with no price at all, and the drives
that were created for those offers and are left with no offer; and the offers waiting in
Review at a price of 0, which could no longer be resolved. The store's next run finds no price
on those pages and records nothing for them.

It only counts, and changes nothing, unless APPLY=1.

Usage, where the backend runs (it has the database's address and SQLAlchemy):
    docker exec -i -e STORE=serverorbit <backend container> python - < remove-zero-prices.py
    docker exec -i -e STORE=serverorbit -e APPLY=1 <backend container> python - < remove-zero-prices.py
"""

import os

from sqlalchemy import create_engine, text

STORE = os.environ["STORE"]
APPLY = os.environ.get("APPLY") == "1"

engine = create_engine(os.environ["DISKTRACKER_DATABASE_URL"])
with engine.connect() as connection:
    counted = {
        "prices of $0.00": connection.execute(
            text(
                "DELETE FROM observations WHERE item_price_cents = 0"
                " AND listing_id IN (SELECT id FROM listings WHERE store = :store)"
            ),
            {"store": STORE},
        ).rowcount
    }
    connection.execute(
        text(
            "CREATE TEMPORARY TABLE unpriced ON COMMIT DROP AS"
            " SELECT id, drive_id FROM listings WHERE store = :store AND NOT EXISTS"
            " (SELECT 1 FROM observations WHERE observations.listing_id = listings.id)"
        ),
        {"store": STORE},
    )
    counted["offers left with no price"] = connection.execute(
        text("DELETE FROM listings WHERE id IN (SELECT id FROM unpriced)")
    ).rowcount
    # Drives made for those offers alone; one another offer still names is kept.
    orphaned = (
        "SELECT drive_id FROM unpriced"
        " WHERE NOT EXISTS (SELECT 1 FROM listings WHERE listings.drive_id = unpriced.drive_id)"
    )
    connection.execute(text(f"DELETE FROM mpn_aliases WHERE drive_id IN ({orphaned})"))
    counted["drives left with no offer"] = connection.execute(
        text(f"DELETE FROM drives WHERE id IN ({orphaned})")
    ).rowcount
    counted["queued for review at $0.00"] = connection.execute(
        text("DELETE FROM unmatched WHERE source = :store AND item_price_cents = 0"),
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
