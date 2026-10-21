#!/usr/bin/env python3
"""Hold the offers collected before their titles and capacities were doubted at collection.

Since the backend's fix, a collected offer that may not be one drive, or whose capacity is more
than any drive holds or other than its own title says, waits for a person in the Review queue,
and what was recorded of its page is held: it counts in no ranking, no prices today and no trend
until a person says what the page is, or the page is next collected without doubt. Offers
recorded before then are still counted. This holds them, by the same rule
(disktracker.catalog.rules.doubt), and queues each one's page for review.

Their prices are kept as they are. An offer entered by hand, or whose page a person has already
settled, is left as it is; so is one already held, so running it again changes nothing.

It only says what it would do, and changes nothing, unless APPLY=1.

Usage, where the backend runs (it has the database's address and the backend's rules):
    docker exec -i <backend container> python - < hold-doubted-offers.py
    docker exec -i -e APPLY=1 <backend container> python - < hold-doubted-offers.py
"""

import os
from datetime import UTC
from uuid import uuid4

from sqlalchemy import create_engine, text

from disktracker.catalog.rules import doubt

APPLY = os.environ.get("APPLY") == "1"
SAID = {
    "not_a_single_drive": "it may not be one drive",
    "implausible_capacity": "its capacity is more than any drive holds or other than its title says",
}

# Every offer with its drive's capacity, its latest price, how many it has had and over when, and
# whether a person has settled what it is or it already waits in the Review queue, as its own
# listing (another offer of its page settles nothing of it); held against being recorded
# meanwhile.
OFFERS = text(
    "SELECT l.id, l.store, l.url, l.seller, d.mpn, l.condition, l.title, l.held_reason,"
    " l.last_checked_at, d.capacity_gb, latest.acquisition_method AS provenance,"
    " latest.item_price_cents, latest.shipping_cents, latest.in_stock,"
    " latest.observed_at AS latest_at, prices.counted, prices.first_at, prices.last_at,"
    " EXISTS (SELECT 1 FROM scraped_matches m WHERE m.source = l.store AND m.url = l.url"
    "  AND m.seller = l.seller AND m.mpn = d.mpn AND m.condition = l.condition"
    "  AND NOT m.ignored) AS settled,"
    " EXISTS (SELECT 1 FROM unmatched u WHERE u.source = l.store AND u.url = l.url"
    "  AND u.seller = l.seller AND u.mpn = d.mpn AND u.condition = l.condition) AS queued"
    " FROM listings l JOIN drives d ON d.id = l.drive_id"
    " JOIN LATERAL (SELECT * FROM observations o WHERE o.listing_id = l.id"
    "  ORDER BY o.observed_at DESC, o.entered_at DESC, o.id DESC LIMIT 1) latest ON true"
    " JOIN LATERAL (SELECT count(*) AS counted, min(o.observed_at) AS first_at,"
    "  max(o.observed_at) AS last_at FROM observations o WHERE o.listing_id = l.id) prices ON true"
    " ORDER BY l.store, l.url, l.id FOR UPDATE OF l"
)
HOLD = text("UPDATE listings SET held_reason = :reason WHERE id = :id")
QUEUE = text(
    "INSERT INTO unmatched (id, source, url, title, seller, mpn, condition, capacity_gb,"
    " item_price_cents, shipping_cents, in_stock, reason, provenance, first_seen_at,"
    " last_seen_at) VALUES (:id, :store, :url, :title, :seller, :mpn, :condition, :capacity_gb,"
    " :item_price_cents, :shipping_cents, :in_stock, :reason, 'collected', :first_at,"
    " :last_seen_at) ON CONFLICT DO NOTHING"
)


def day(moment):
    return moment.astimezone(UTC).date().isoformat()


engine = create_engine(os.environ["DISKTRACKER_DATABASE_URL"])
with engine.connect() as db:
    holding, entered, settled, already = [], 0, 0, 0
    for offer in db.execute(OFFERS).mappings():
        if offer["held_reason"] is not None:
            already += 1
            continue
        reason = doubt(offer["title"], offer["capacity_gb"], offer["mpn"])
        if reason is None:
            continue
        if offer["provenance"] != "collected":
            entered += 1
        elif offer["settled"]:
            settled += 1
        else:
            holding.append((offer, reason))

    lines = []
    for offer, reason in holding:
        db.execute(HOLD, {"id": offer["id"], "reason": reason})
        if offer["url"] is None:
            queue = "it has no page to queue, so settle it by hand"
        elif offer["queued"]:
            queue = "already queued for review"
        else:
            queue = "queued for review"
            last_seen = max(offer["latest_at"], offer["last_checked_at"] or offer["latest_at"])
            db.execute(
                QUEUE,
                {**offer, "id": uuid4(), "reason": reason, "last_seen_at": last_seen},
            )
        prices = f"{offer['counted']} price{'' if offer['counted'] == 1 else 's'}"
        lines.append(
            f"  {offer['url']}: {offer['mpn']}, {offer['condition']}, {offer['title']!r}:"
            f" {SAID[reason]}. {prices} kept, {day(offer['first_at'])} to"
            f" {day(offer['last_at'])}; {queue}."
        )
    if APPLY:
        db.commit()
    else:
        db.rollback()

verb = "Held" if APPLY else "Would hold"
print(
    f"{verb} {len(holding)} offers while a person settles what their pages are{':' if holding else '.'}"
)
for line in lines:
    print(line)
if holding:
    print(
        "Their prices are kept as they are. Held, an offer counts in no ranking, no prices today"
        " and no trend until a person says what its page is, or it is next collected without"
        " doubt."
    )
print(
    f"Left as they are: {entered} entered by hand, {settled} settled by a person,"
    f" {already} already held."
)
if not APPLY:
    print("Nothing was changed. Run again with APPLY=1 to hold them.")
