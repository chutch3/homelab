#!/usr/bin/env python3
"""Seed DiskTracker with real listings pulled from multiple stores on 2026-09-22.

Includes one drive (Seagate Exos X18, MPN ST18000NM000J) listed at three real
sources with three real prices, to demonstrate cross-store price comparison
for the same physical drive.

Safe to run more than once: offers already present (matched by MPN, store, seller
and condition) are skipped rather than given a duplicate price.

Usage: DISKTRACKER_API_ORIGIN=http://127.0.0.1:8000 python3 seed-examples.py
"""
import json
import os
import urllib.request
import uuid
from datetime import datetime, timezone

ORIGIN = os.environ.get("DISKTRACKER_API_ORIGIN", "http://127.0.0.1:8000")
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

LISTINGS = [
    {
        "title": "Seagate Exos X20 ST18000NM003D 18TB 7.2K RPM SATA 6Gb/s 512e 256MB 3.5in Recertified Hard Drive",
        "mpn": "ST18000NM003D", "store": "serverpartdeals", "seller": "", "price": 49900, "capacity": "18.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/seagate-exos-x20-st18000nm003d-18tb-7-2k-rpm-sata-6gb-s-3-5-recertified-hard-drive",
        "interface": "sata",
    },
    {
        "title": "Seagate Exos ST28000NM000C 28TB 7.2K RPM SATA 6Gb/s 512e CMR 3.5in Recertified Hard Drive",
        "mpn": "ST28000NM000C", "store": "serverpartdeals", "seller": "", "price": 82900, "capacity": "28.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/seagate-exos-st28000nm000c-28tb-7-2k-rpm-sata-6gb-s-512e-cmr-3-5-recertified-hard-drive",
        "interface": "sata", "recording_type": "cmr",
    },
    {
        "title": "Seagate Exos ST22000NM000C 22TB 7.2K RPM SATA 6Gb/s 3.5in Recertified Hard Drive",
        "mpn": "ST22000NM000C", "store": "serverpartdeals", "seller": "", "price": 64900, "capacity": "22.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/seagate-exos-st22000nm000c-22tb-7-2k-rpm-sata-6gb-s-3-5-recertified-hard-drive",
        "interface": "sata",
    },
    {
        "title": "Western Digital Ultrastar DC HC550 WUH721818ALE604 0F38453 18TB 7.2K RPM SATA 6Gb/s 512e Power Disable 3.5in Recertified HDD",
        "mpn": "WUH721818ALE604", "store": "serverpartdeals", "seller": "", "price": 48900, "capacity": "18.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/western-digital-ultrastar-dc-hc550-wuh721818ale604-0f38453-18tb-7-2k-rpm-sata-6gb-s-3-5-recertified-hard-drive",
        "interface": "sata",
    },
    {
        "title": "Toshiba 14TB MG07 MG07ACA14TEY 7.2K RPM SATA 6Gb/s 512e SIE 3.5in Refurbished HDD",
        "mpn": "MG07ACA14TEY", "store": "serverpartdeals", "seller": "", "price": 29900, "capacity": "14.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/toshiba-mg07-mg07aca14tey-14tb-7-2k-rpm-sata-6gb-s-512e-sie-3-5-refurbished-hdd",
        "interface": "sata",
    },
    {
        "title": "Western Digital Ultrastar DC HC580 WUH722424ALE604 0F62798 24TB 7.2K RPM SATA 6Gb/s 512e Power Disable 3.5in Recertified Hard Drive",
        "mpn": "WUH722424ALE604", "store": "serverpartdeals", "seller": "", "price": 65900, "capacity": "24.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/western-digital-ultrastar-dc-hc580-wuh722424ale604-0f62798-24tb-7-2k-rpm-sata-6gb-s-512e-3-5-recertified-hard-drive",
        "interface": "sata",
    },
    {
        "title": "Toshiba MG08 MG08ACA16TE 16TB 7.2K RPM SATA 6Gb/s 3.5in Refurbished HDD",
        "mpn": "MG08ACA16TE", "store": "serverpartdeals", "seller": "", "price": 42800, "capacity": "16.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/toshiba-mg08-mg08aca16te-16tb-7-2k-rpm-sata-6gb-s-3-5-refurbished-hdd",
        "interface": "sata",
    },
    # Seagate Exos X18 (ST18000NM000J) at three real sources, so the app can
    # actually demonstrate its point: same drive, three real prices.
    {
        "title": "Seagate Exos X18 ST18000NM000J 18TB 7.2K RPM SATA 6Gb/s 512e/4Kn 256MB 3.5\" FastFormat HDD",
        "mpn": "ST18000NM000J", "store": "serverpartdeals", "seller": "", "price": 36999, "capacity": "18.00",
        "condition": "refurbished",
        "url": "https://www.serverpartdeals.com/collections/hard-drives/products/seagate-exos-x18-st18000nm000j-18tb-7-2k-rpm-sata-6gb-s-512e-4kn-256mb-3-5-hdd",
        "interface": "sata",
    },
    {
        "title": "Seagate 18TB Exos X18 7200 RPM SATA 6Gb/s 256MB Cache 3.5-Inch Enterprise Hard Drive HDD (ST18000NM000J)",
        "mpn": "ST18000NM000J", "store": "other", "seller": "E.O.L. Tech Inc. (Newegg)", "price": 52999, "capacity": "18.00",
        "condition": "new",
        "url": "https://www.newegg.com/seagate-exos-x18-st18000nm000j-18tb/p/1B4-00VK-00616",
        "interface": "sata",
    },
    {
        "title": "Seagate Exos X18 (7200RPM, 3.5-inch, SATA III, Standard Format) 18TB Internal Enterprise Drive - ST18000NM000J",
        "mpn": "ST18000NM000J", "store": "other", "seller": "Beach Audio (eBay)", "price": 88453, "capacity": "18.00",
        "condition": "new",
        "url": "https://www.ebay.com/p/28041516768",
        "interface": "sata",
    },
]


def get(path: str) -> dict:
    with urllib.request.urlopen(f"{ORIGIN}{path}") as response:
        return json.loads(response.read())


def send(method: str, path: str, payload: dict) -> dict:
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        f"{ORIGIN}{path}", data=body, method=method,
        headers={"Content-Type": "application/json", "Idempotency-Key": str(uuid.uuid4())},
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read())


def specification(listing: dict) -> dict:
    # Every example is a 3.5" hard drive.
    spec = {"media_type": "hdd", "form_factor": "3_5", "interface": listing["interface"]}
    if "recording_type" in listing:
        spec["recording_type"] = listing["recording_type"]
    return spec


existing = {
    (row["mpn"], row["store"], row["seller"], row["condition"]) for row in get("/api/listings")
}

for listing in LISTINGS:
    name = f"{listing['store']} {listing['seller']}".strip()
    if (listing["mpn"], listing["store"], listing["seller"], listing["condition"]) in existing:
        print(f"skipped (already seeded)  {name}: {listing['title'][:60]}")
        continue
    saved = send("POST", "/api/prices", {
        "mpn": listing["mpn"], "store": listing["store"], "seller": listing["seller"],
        "condition": listing["condition"],
        "title": listing["title"], "url": listing["url"], "capacity_gb": round(float(listing["capacity"]) * 1000),
        "item_price_cents": listing["price"], "observed_at": NOW,
        "notes": f"Seeded from {name} on 2026-09-22",
    })
    drive = saved["drive"]
    # Specs belong to the drive, so only the first seller seeded for an MPN sets them.
    if drive["specifications"]["interface"] == "unknown":
        send("PUT", f"/api/drives/{drive['id']}/specifications", {
            "capacity_gb": drive["capacity_gb"], "specifications": specification(listing),
        })
    print(f"created {saved['id']}  {name}: {listing['title'][:60]}")
