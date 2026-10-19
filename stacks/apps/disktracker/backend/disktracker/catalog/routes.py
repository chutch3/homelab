"""The catalog over HTTP: offers and their prices, drives, the Review queue, and the rules that
read listing text. Routes read the request, ask the service, and declare what they return."""

from typing import Annotated, Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Header, Query
from fastapi.responses import Response
from listing_text.listing import read_listing
from listing_text.readers import condition_rules

from disktracker.catalog.schemas import (
    AliasInput,
    CatalogDrivePage,
    CatalogDriveQuery,
    ConditionRule,
    DecisionResult,
    Drive,
    DriveDetail,
    DriveEdit,
    DriveInput,
    DrivePage,
    DriveQuery,
    IgnoreDecision,
    ListingFacts,
    ListingText,
    MatchDecision,
    Offer,
    OfferEdit,
    OfferQuery,
    OfferSummary,
    PriceInput,
    PricePage,
    PriceQuery,
    PriceResult,
    RangeQuery,
    ReviewItem,
    ReviewReason,
    StoreKey,
)
from disktracker.catalog.service import CatalogService
from disktracker.container import Container
from disktracker.errors import ErrorResponse

router = APIRouter(prefix="/api")


Catalog = Annotated[CatalogService, Depends(Provide[Container.catalog_service])]


class Paging:
    """Which part of a long list a request asks for: limit items after skipping offset. A route
    that lists takes this, and answers through paged()."""

    def __init__(
        self,
        limit: Annotated[
            int | None,
            Query(ge=1, le=500, description="Maximum items; omit to return all remaining matches."),
        ] = None,
        offset: Annotated[int, Query(ge=0, description="Number of matching items to skip.")] = 0,
    ) -> None:
        self.limit, self.offset = limit, offset


def paged[T](response: Response, found: tuple[list[T], int]) -> list[T]:
    """The part of a list that was asked for, with how many there are in all, whatever the
    limit, in X-Total-Count."""
    items, total = found
    response.headers["X-Total-Count"] = str(total)
    return items


@router.get(
    "/drives", response_model=DrivePage, tags=["Drives"], summary="Browse and filter drives"
)
@inject
def list_drives(catalog: Catalog, query: Annotated[DriveQuery, Query()]) -> dict[str, Any]:
    """The drives that match, a page at a time, each shown by its cheapest matching offer in
    stock, with the lowest prices among every match and the filter options of every drive.

    Repeat a parameter for several choices, e.g. `brand=Seagate&brand=Toshiba`. Choices within
    a filter use OR; different filters use AND. Filters match offers, then group them by drive.
    Each filter option counts the drives choosing it would give, with every other filter as
    asked. total counts matching drives before pagination; offers counts matching offers.
    """
    return catalog.drives(query)


@router.post(
    "/drives",
    status_code=201,
    response_model=Drive,
    tags=["Drives"],
    summary="Make a drive",
    responses={409: {"model": ErrorResponse, "description": "The MPN already identifies a drive"}},
)
@inject
def create_drive(catalog: Catalog, entry: DriveInput) -> dict[str, Any]:
    """Make a drive before any price of it, under an MPN that no drive goes by, as its own MPN or
    another of its MPNs. A drive already going by it is never merged with this one."""
    return catalog.create_drive(entry)


@router.get(
    "/catalog-drives",
    response_model=CatalogDrivePage,
    tags=["Drives"],
    summary="List every drive to manage",
)
@inject
def list_catalog_drives(
    catalog: Catalog, query: Annotated[CatalogDriveQuery, Query()]
) -> dict[str, Any]:
    """Every drive, offers held for review and all, a page at a time: those named by q exactly
    (by MPN or another MPN) first, then in stock first and cheapest per terabyte first. Each has
    how many offers it has and what it needs; issues counts every drive needing each."""
    return catalog.catalog_drives(query)


@router.get(
    "/drives/{drive_id}",
    response_model=DriveDetail,
    tags=["Drives"],
    summary="Get a drive and its offers",
    responses={404: {"model": ErrorResponse, "description": "Drive not found"}},
)
@inject
def get_drive(
    catalog: Catalog, drive_id: UUID, query: Annotated[RangeQuery, Query()]
) -> dict[str, Any]:
    """A drive with every offer of it, and the range of its price in each condition."""
    return catalog.drive(drive_id, query)


@router.get(
    "/offers",
    response_model=list[OfferSummary],
    tags=["Offers"],
    summary="List offers with their latest prices",
)
@inject
def list_offers(catalog: Catalog, query: Annotated[OfferQuery, Query()]) -> list[dict[str, Any]]:
    """Return latest-price summaries, optionally narrowed by store or drive, ordered by title.
    With needs_recheck, return all manually priced offers not checked within recent_days,
    oldest checks first; store and drive filters are not applied in this mode. This list is
    not paginated."""
    return catalog.list_offers(query)


@router.get("/prices", response_model=PricePage, tags=["Prices"], summary="Read price history")
@inject
def list_prices(catalog: Catalog, query: Annotated[PriceQuery, Query()]) -> dict[str, Any]:
    """Supply exactly one of drive_id or offer_id. Return observations oldest first, ordered by
    observed_at, entered_at and id, using limit/offset pagination. since and until are inclusive;
    the result also includes each offer's last observation before since to establish the price
    in effect when the window opens. total counts matching observations, including those opening
    values, before pagination. An unknown drive or offer returns an empty page."""
    return catalog.prices(query)


@router.post(
    "/prices",
    status_code=201,
    response_model=PriceResult,
    responses={
        201: {
            "description": "Recorded, or an unchanged price counted as a check (price_id is null)",
            "content": {
                "application/json": {
                    "example": {
                        "status": "recorded",
                        "offer_id": "11111111-1111-4111-8111-111111111111",
                        "price_id": "22222222-2222-4222-8222-222222222222",
                        "review_item_id": None,
                    }
                }
            },
        },
        202: {
            "model": PriceResult,
            "description": "Queued for review",
            "content": {
                "application/json": {
                    "example": {
                        "status": "queued",
                        "offer_id": None,
                        "price_id": None,
                        "review_item_id": "33333333-3333-4333-8333-333333333333",
                    }
                }
            },
        },
        200: {
            "model": PriceResult,
            "description": "Ignored: nothing was kept",
            "content": {
                "application/json": {
                    "example": {
                        "status": "ignored",
                        "offer_id": None,
                        "price_id": None,
                        "review_item_id": None,
                    }
                }
            },
        },
        404: {"model": ErrorResponse, "description": "The named offer does not exist"},
        409: {
            "model": ErrorResponse,
            "description": "The idempotency key was used for a different body, or capacity conflicts",
        },
    },
    tags=["Prices"],
    summary="Record a manual or collected price",
)
@inject
def record_price(
    catalog: Catalog,
    entry: Annotated[
        PriceInput,
        Body(
            openapi_examples={
                "manual": {
                    "summary": "Manually describe an offer",
                    "value": {
                        "store": "other",
                        "seller": "Example seller",
                        "mpn": "ST18000NM000J",
                        "condition": "manufacturer_recertified",
                        "capacity_gb": 18000,
                        "title": "Seagate Exos X18",
                        "item_price_cents": 18900,
                        "shipping_cents": 0,
                    },
                },
                "existing_offer": {
                    "summary": "Price an existing offer (replace the example UUID)",
                    "value": {
                        "offer_id": "11111111-1111-4111-8111-111111111111",
                        "item_price_cents": 17900,
                    },
                },
                "collected": {
                    "summary": "Queue an unmatched collected offer",
                    "value": {
                        "store": "serverpartdeals",
                        "provenance": "collected",
                        "on_unmatched": "queue",
                        "title": "18 TB hard drive",
                        "url": "https://example.com/drives/18tb",
                        "capacity_gb": 18000,
                        "item_price_cents": 18900,
                        "shipping_cents": None,
                    },
                },
                "out_of_stock": {
                    "summary": "Mark a previously priced offer out of stock",
                    "value": {
                        "offer_id": "11111111-1111-4111-8111-111111111111",
                        "in_stock": False,
                    },
                },
            }
        ),
    ],
    idempotency_key: Annotated[
        UUID,
        Header(
            description="New UUID for each submission. Retry using the same key and body; changing the body returns 409."
        ),
    ],
    response: Response,
) -> dict[str, Any]:
    """Record a price, whoever submits it. The Idempotency-Key names the submission: sent again
    with the same body it is answered as it was the first time, without doing the work again;
    sent with a different body it is refused (409).

    Either name offer_id (omit store, MPN and condition), or describe the offer with store,
    MPN and condition. Store `other` also requires seller. A new drive needs capacity_gb.
    With on_unmatched=queue, MPN and condition may be absent, but title and URL are required.
    An in-stock observation needs a positive item price. An out-of-stock observation without
    a price reuses the last price; a manual entry cannot do this for an offer never priced.
    Collected observations also honor saved review decisions and ignore never-priced sold-out
    offers. provenance defaults to manual and on_unmatched defaults to reject.
    """
    result = catalog.record_price(entry, idempotency_key)
    response.status_code = {"recorded": 201, "queued": 202, "ignored": 200}[result["status"]]
    return result


@router.get(
    "/review-items",
    response_model=list[ReviewItem],
    tags=["Review"],
    summary="List offers waiting for review",
    responses={
        200: {
            "headers": {
                "X-Total-Count": {
                    "description": "Number of items matching store and reason before pagination.",
                    "schema": {"type": "integer", "minimum": 0},
                }
            }
        }
    },
)
@inject
def review_items(
    catalog: Catalog,
    response: Response,
    paging: Annotated[Paging, Depends()],
    store: StoreKey | None = None,
    reason: ReviewReason | None = None,
) -> list[dict[str, Any]]:
    """The offers waiting for review, newest first; by store and reason, and a part at a time,
    when asked. X-Total-Count says how many there are in all, whatever the limit."""
    return paged(response, catalog.review_items(store, reason, paging.limit, paging.offset))


@router.put(
    "/review-items/{item_id}/decision",
    response_model=DecisionResult,
    tags=["Review"],
    summary="Match or ignore a review item",
    responses={
        404: {"model": ErrorResponse, "description": "Review item not found"},
        409: {
            "model": ErrorResponse,
            "description": "A different decision was already recorded, or the capacity conflicts",
        },
    },
)
@inject
def decide(
    catalog: Catalog,
    item_id: UUID,
    # Body() would drop the union's discriminator; given here, a decision is checked as what it
    # decides.
    decision: Annotated[MatchDecision | IgnoreDecision, Body(discriminator="decision")],
) -> dict[str, Any]:
    """Say what a review item is. Sent again, the same decision gets the first answer without
    doing anything more, so a decision whose answer was lost can be retried; a different decision
    is refused (409)."""
    return catalog.decide(item_id, decision)


@router.get(
    "/offers/{offer_id}",
    response_model=Offer,
    tags=["Offers"],
    summary="Get an offer and its price history",
    responses={404: {"model": ErrorResponse, "description": "Offer not found"}},
)
@inject
def get_offer(catalog: Catalog, offer_id: UUID) -> dict[str, Any]:
    """Return an offer and its full price history, oldest first. Use GET /api/prices for a
    paginated history window."""
    return catalog.offer(offer_id)


@router.patch(
    "/offers/{offer_id}",
    response_model=Offer,
    tags=["Offers"],
    summary="Edit offer details",
    responses={404: {"model": ErrorResponse, "description": "Offer not found"}},
)
@inject
def edit_offer(catalog: Catalog, offer_id: UUID, entry: OfferEdit) -> dict[str, Any]:
    """Change the supplied title or URL; omitted fields stay unchanged. A null URL clears it. MPN,
    store, seller and condition identify the offer and cannot be edited here."""
    return catalog.edit_offer(offer_id, entry)


@router.delete(
    "/offers/{offer_id}",
    status_code=204,
    tags=["Offers"],
    summary="Delete an offer and its prices",
    responses={404: {"model": ErrorResponse, "description": "Offer not found"}},
)
@inject
def delete_offer(catalog: Catalog, offer_id: UUID) -> None:
    """Delete the offer and all its prices. The drive remains. An unknown offer returns 404."""
    catalog.delete_offer(offer_id)


@router.delete("/prices/{price_id}", status_code=204, tags=["Prices"], summary="Delete a price")
@inject
def delete_price(catalog: Catalog, price_id: UUID) -> None:
    """Remove a price recorded by mistake; an offer whose last price it was goes with it. A price
    that is not there, deleted already or never kept, is answered the same way."""
    catalog.delete_price(price_id)


@router.post(
    "/listing-text",
    response_model=ListingFacts,
    tags=["Listing tools"],
    summary="Extract drive details from listing text",
)
@inject
def read_listing_text(catalog: Catalog, entry: ListingText) -> dict[str, object]:
    """Extract MPN, capacity, condition, brand and price from pasted text using the current
    condition rules. Missing facts are null. This operation saves nothing."""
    conditions = condition_rules(
        (rule["pattern"], rule["condition"]) for rule in catalog.list_condition_rules()
    )
    return read_listing(entry.text, conditions)._asdict()


@router.get(
    "/condition-rules",
    response_model=list[ConditionRule],
    tags=["Listing tools"],
    summary="List condition recognition rules",
)
@inject
def list_condition_rules(catalog: Catalog) -> list[dict[str, Any]]:
    """Return condition recognition rules in priority order. The first matching case-insensitive
    regular expression wins."""
    return catalog.list_condition_rules()


@router.put(
    "/condition-rules",
    response_model=list[ConditionRule],
    tags=["Listing tools"],
    summary="Replace condition recognition rules",
)
@inject
def replace_condition_rules(catalog: Catalog, rules: list[ConditionRule]) -> list[dict[str, Any]]:
    """Replace the entire ordered list of condition recognition rules. An empty list removes all
    rules; the first matching pattern wins."""
    return catalog.replace_condition_rules(rules)


@router.post(
    "/drives/{drive_id}/aliases",
    status_code=201,
    response_model=Drive,
    tags=["Drives"],
    summary="Add an alternate MPN or merge drives",
    responses={
        404: {"model": ErrorResponse, "description": "Drive not found"},
        409: {
            "model": ErrorResponse,
            "description": "The MPN is this drive's canonical MPN or is already a registered alias",
        },
    },
)
@inject
def add_alias(catalog: Catalog, drive_id: UUID, entry: AliasInput) -> dict[str, Any]:
    """Declare another MPN for this drive. If it is another drive's canonical MPN, merge that
    drive's offers, price history and aliases into this drive, retaining this drive's capacity
    and specifications. Matching offers combine their histories. The target's own canonical
    MPN or an already registered alias returns 409."""
    return catalog.add_alias(drive_id, entry.mpn)


@router.patch(
    "/drives/{drive_id}",
    response_model=Drive,
    tags=["Drives"],
    summary="Correct drive details",
    responses={404: {"model": ErrorResponse, "description": "Drive not found"}},
)
@inject
def edit_drive(catalog: Catalog, drive_id: UUID, entry: DriveEdit) -> dict[str, Any]:
    """Correct a drive: what is given changes, and what is left out stays."""
    return catalog.edit_drive(drive_id, entry)
