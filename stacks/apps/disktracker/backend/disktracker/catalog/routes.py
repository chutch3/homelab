"""The catalog over HTTP: offers and their prices, drives, the Review queue, and the rules that
read listing text. Routes read the request, ask the service, and declare what they return."""

from typing import Annotated, Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Body, Depends, Header, Query
from fastapi.responses import Response
from listing_text.listing import read_listing
from listing_text.readers import condition_rules

from disktracker.catalog.condition_rule_service import ConditionRuleService
from disktracker.catalog.drive_service import DriveService
from disktracker.catalog.ingestion_service import IngestionService
from disktracker.catalog.offer_service import OfferService
from disktracker.catalog.price_service import PriceService
from disktracker.catalog.review_service import ReviewService
from disktracker.catalog.schemas import (
    AliasInput,
    CatalogDrivePage,
    CatalogDriveQuery,
    ConditionRule,
    DecisionResult,
    Drive,
    DriveEdit,
    DriveInput,
    DriveLookup,
    FoundDrives,
    IgnoreDecision,
    IngestionInput,
    ListingFacts,
    ListingText,
    MatchDecision,
    MergeInput,
    MergeResult,
    Offer,
    OfferEdit,
    OfferQuery,
    OfferSummary,
    PriceInput,
    PricePage,
    PriceQuery,
    PriceResult,
    ReviewItem,
    ReviewReason,
    StoreKey,
)
from disktracker.catalog.service import CatalogService
from disktracker.container import Container
from disktracker.errors import ErrorResponse

router = APIRouter(prefix="/api")


Catalog = Annotated[CatalogService, Depends(Provide[Container.catalog_service])]
Offers = Annotated[OfferService, Depends(Provide[Container.offer_service])]
Rules = Annotated[ConditionRuleService, Depends(Provide[Container.condition_rule_service])]
Prices = Annotated[PriceService, Depends(Provide[Container.price_service])]
Ingestion = Annotated[IngestionService, Depends(Provide[Container.ingestion_service])]
Reviews = Annotated[ReviewService, Depends(Provide[Container.review_service])]
Drives = Annotated[DriveService, Depends(Provide[Container.drive_service])]


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


@router.post(
    "/drives",
    status_code=201,
    response_model=Drive,
    tags=["Drives"],
    summary="Make a drive",
    responses={409: {"model": ErrorResponse, "description": "The MPN already identifies a drive"}},
)
@inject
def create_drive(drives: Drives, entry: DriveInput) -> dict[str, Any]:
    """Make a drive before any price of it, under an MPN that no drive goes by, as its own MPN or
    another of its MPNs. A drive already going by it is never merged with this one."""
    return drives.create(entry)


@router.post(
    "/drives/{source_id}/merge",
    response_model=MergeResult,
    tags=["Drives"],
    summary="Merge a drive into another",
    responses={
        404: {"model": ErrorResponse, "description": "Drive not found"},
        409: {
            "model": ErrorResponse,
            "description": "The drives differ on what both know, or the save key was used for another merge",
        },
    },
)
@inject
def merge_drive(
    drives: Drives,
    source_id: UUID,
    entry: MergeInput,
    idempotency_key: Annotated[
        UUID,
        Header(
            description="New UUID for each merge; sent again with the same body, it is answered as it was."
        ),
    ],
) -> dict[str, Any]:
    """Merge the drive into the target, which survives: with every MPN the drive went by (its
    own and its others), its brand where the target has none, its specifications where the
    target's are unknown, and its offers. An offer of the same store, seller and condition as
    one of the target's is combined into the target's: its prices are kept, it stays held if
    either was, and it was last checked when either was. Drives that both know a capacity or a
    specification and differ on it are not merged (409): correct one first. Sent again under the
    same Idempotency-Key it is answered as it was; the answer names the offers as they were."""
    return drives.merge(source_id, entry, idempotency_key)


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
    "/drives",
    response_model=FoundDrives,
    tags=["Drives"],
    summary="Find drives by MPN or words",
)
@inject
def find_drives(drives: Drives, query: Annotated[DriveLookup, Query()]) -> dict[str, Any]:
    """The drive that goes by an MPN (mpn, as its own or another of its MPNs; at most one), or
    the drives any name of which has some words (q): its MPN, another of its MPNs, or any name an
    offer of it goes by, held offers too; those the words are an MPN of first. Each is named by
    the title of its cheapest offer in stock, else its cheapest offer, else its MPN."""
    return drives.find(query)


@router.get(
    "/drives/{drive_id}",
    response_model=Drive,
    tags=["Drives"],
    summary="Get a drive",
    responses={404: {"model": ErrorResponse, "description": "Drive not found"}},
)
@inject
def get_drive(drives: Drives, drive_id: UUID) -> dict[str, Any]:
    """A drive with every other MPN it goes by. Its offers are GET /offers?drive_id=; the range
    of its price in each condition is GET /reports/price-ranges."""
    return drives.get(drive_id)


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
        404: {"model": ErrorResponse, "description": "The named offer or drive does not exist"},
        409: {
            "model": ErrorResponse,
            "description": "The idempotency key was used for a different body",
        },
    },
    tags=["Prices"],
    summary="Record a price of a known drive's offer",
)
@inject
def record_price(
    prices: Prices,
    entry: Annotated[
        PriceInput,
        Body(
            openapi_examples={
                "drive": {
                    "summary": "Price a drive at a store (replace the example UUID)",
                    "value": {
                        "drive_id": "44444444-4444-4444-8444-444444444444",
                        "store": "other",
                        "seller": "Example seller",
                        "condition": "manufacturer_recertified",
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
) -> dict[str, Any]:
    """Record a price of an offer whose drive is already known. The Idempotency-Key names the
    submission: sent again with the same body it is answered as it was the first time, without
    doing the work again; sent with a different body it is refused (409).

    Either name offer_id, or name drive_id with the store, seller and condition it is offered in
    (store `other` also requires seller); an offer new to them is made, with title and url when
    given, else titled by its drive's MPN. What says what a drive is (its MPN, capacity, brand,
    specifications or other MPNs) is refused: make or correct the drive first (POST /drives,
    PATCH /drives/{id}). A store page as collected is taken in at POST /ingestions; a collector
    sends here only a recheck of an offer it names (provenance collected), which never releases
    the offer's hold.

    An in-stock observation needs a positive item price. An out-of-stock observation without a
    price reuses the last price; a manual entry cannot do this for an offer never priced. An
    unchanged price is recorded with price_id null, counted as a check."""
    return prices.record(entry, idempotency_key)


@router.post(
    "/ingestions",
    status_code=201,
    response_model=PriceResult,
    responses={
        201: {
            "description": "Recorded, or an unchanged price counted as a check (price_id is null)"
        },
        202: {"model": PriceResult, "description": "Queued for review"},
        200: {"model": PriceResult, "description": "Ignored: nothing was kept"},
        409: {
            "model": ErrorResponse,
            "description": "The idempotency key was used for a different body",
        },
    },
    tags=["Prices"],
    summary="Take in a collected store page",
)
@inject
def ingest(
    ingestion: Ingestion,
    entry: IngestionInput,
    idempotency_key: Annotated[
        UUID,
        Header(
            description="New UUID for each observation. Retry using the same key and body; changing the body returns 409."
        ),
    ],
    response: Response,
) -> dict[str, Any]:
    """Take in one observation of a store page as collected: match it to a drive (registering
    one new under a known MPN and capacity), record its price, or queue it for review when it
    cannot be matched or is in doubt, or ignore it as an earlier review decided. One
    observation, one outcome: the Idempotency-Key answers it again as it was the first time,
    without doing the work again, and refuses a different body (409).

    A price of an offer already known by id, a recheck among them, goes to POST /prices: it
    gives no new evidence of what the page is."""
    result = ingestion.ingest(entry, idempotency_key)
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
    reviews: Reviews,
    item_id: UUID,
    # Body() would drop the union's discriminator; given here, a decision is checked as what it
    # decides.
    decision: Annotated[MatchDecision | IgnoreDecision, Body(discriminator="decision")],
) -> dict[str, Any]:
    """Say what a review item is. Sent again, the same decision gets the first answer without
    doing anything more, so a decision whose answer was lost can be retried; a different decision
    is refused (409)."""
    return reviews.decide(item_id, decision)


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
def edit_offer(offers: Offers, offer_id: UUID, entry: OfferEdit) -> dict[str, Any]:
    """Change the supplied title or URL; omitted fields stay unchanged. A null URL clears it. The
    drive, store, seller and condition identify the offer and cannot be edited here."""
    return offers.edit(offer_id, entry)


@router.delete(
    "/offers/{offer_id}",
    status_code=204,
    tags=["Offers"],
    summary="Delete an offer and its prices",
    responses={404: {"model": ErrorResponse, "description": "Offer not found"}},
)
@inject
def delete_offer(offers: Offers, offer_id: UUID) -> None:
    """Delete the offer and all its prices. The drive remains. An unknown offer returns 404."""
    offers.delete(offer_id)


@router.delete("/prices/{price_id}", status_code=204, tags=["Prices"], summary="Delete a price")
@inject
def delete_price(offers: Offers, price_id: UUID) -> None:
    """Remove a price recorded by mistake; an offer whose last price it was goes with it. A price
    that is not there, deleted already or never kept, is answered the same way."""
    offers.delete_price(price_id)


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
def replace_condition_rules(replaced: Rules, rules: list[ConditionRule]) -> list[dict[str, Any]]:
    """Replace the entire ordered list of condition recognition rules. An empty list removes all
    rules; the first matching pattern wins."""
    return replaced.replace(rules)


@router.post(
    "/drives/{drive_id}/aliases",
    status_code=201,
    response_model=Drive,
    tags=["Drives"],
    summary="Add an alternate MPN",
    responses={
        404: {"model": ErrorResponse, "description": "Drive not found"},
        409: {
            "model": ErrorResponse,
            "description": "A drive already goes by the MPN",
        },
    },
)
@inject
def add_alias(drives: Drives, drive_id: UUID, entry: AliasInput) -> dict[str, Any]:
    """Declare another MPN this drive goes by: one no drive goes by yet. An MPN any drive already
    goes by, as its own or another of its MPNs, is refused (409) naming that drive, and nothing
    changes. To join two drives, merge one into the other (POST /drives/{source_id}/merge)."""
    return drives.add_alias(drive_id, entry.mpn)


@router.patch(
    "/drives/{drive_id}",
    response_model=Drive,
    tags=["Drives"],
    summary="Correct drive details",
    responses={404: {"model": ErrorResponse, "description": "Drive not found"}},
)
@inject
def edit_drive(drives: Drives, drive_id: UUID, entry: DriveEdit) -> dict[str, Any]:
    """Correct a drive: what is given changes, and what is left out stays."""
    return drives.edit(drive_id, entry)
