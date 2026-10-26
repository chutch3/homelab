"""How the API describes itself: its title, what it is for, its tags, and how its docs page
shows it."""

from typing import Any

OPENAPI: dict[str, Any] = {
    "title": "DiskTracker API",
    "description": (
        "Track drive offers and their price history. A **drive** identifies a model by MPN; "
        "an **offer** identifies that drive at a store, seller and condition; a **price** "
        "records an observation of the offer. **Sources** configure stores and collectors.\n\n"
        "Start with `GET /api/drives` to browse, then use `POST /api/prices` for either "
        "manual or collected prices. Each new submission needs a new UUID Idempotency-Key; "
        "retry with the original key and body. Collection workers register a run, report "
        "progress, and finish it; heartbeats identify all runs the worker still owns.\n\n"
        "Money fields ending in `_cents` are integer US cents. `price_per_tb` is a decimal "
        "dollar string. Capacity uses decimal GB (1 TB = 1,000 GB). Supply timezone-aware "
        "timestamps. Reports use item prices without shipping; offer totals include known "
        "shipping, treating unknown shipping as zero."
    ),
    "openapi_tags": [
        {
            "name": "Drives",
            "description": "Browse models, correct specifications and merge alternate MPNs.",
        },
        {"name": "Offers", "description": "Manage a drive's offers at stores and sellers."},
        {
            "name": "Prices",
            "description": "Record manual or collected prices and read their history.",
        },
        {
            "name": "Review",
            "description": "Match or ignore collected and manually queued offers.",
        },
        {
            "name": "Listing tools",
            "description": "Extract listing details and configure condition recognition.",
        },
        {
            "name": "Sources",
            "description": "Configure stores, test readers and request collection.",
        },
        {
            "name": "Collection",
            "description": "Worker run lifecycle, progress, heartbeat and status.",
        },
        {
            "name": "Reports",
            "description": "Market trends and current item prices per terabyte.",
        },
    ],
    "swagger_ui_parameters": {
        "docExpansion": "none",
        "filter": True,
        "defaultModelsExpandDepth": 0,
        "displayRequestDuration": True,
    },
}
