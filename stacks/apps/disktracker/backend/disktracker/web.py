"""Composition root and HTTP boundary for the drive price application."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from listing_text.listing import read_listing
from listing_text.readers import condition_rules
from sqlalchemy import create_engine

from disktracker.collector import CollectorClient, CollectorUnavailable
from disktracker.kinds import KINDS, SettingsInvalid, checked_settings
from disktracker.mpn import normalize_mpn
from disktracker.responses import (
    Drive,
    Listing,
    ListingFacts,
    ListingSummary,
    ScrapedResult,
    SourceInspection,
    SourceKindView,
    SourcePreview,
    SourceView,
    Unmatched,
    UnmatchedReason,
)
from disktracker.rules import (
    CapacityConflict,
    CapacityRequired,
    PriceRequired,
    preview_verdict,
    source_key,
)
from disktracker.schemas import (
    Activity,
    ActivityAnswer,
    AliasInput,
    CollectorRun,
    CollectorStatus,
    ConditionRule,
    DriveSpecifications,
    ListingText,
    OfferEdit,
    PriceInput,
    Resolution,
    ScrapedInput,
    SourceInput,
    SourceInspectionInput,
    SourcePreviewInput,
    StoreKey,
)
from disktracker.storage import (
    AliasConflict,
    DriveNotFound,
    IdempotencyConflict,
    ListingNotFound,
    PostgresListings,
    SourceExists,
    SourceKept,
    SourceNotFound,
    UnknownStore,
    UnmatchedNotFound,
)


class Paging:
    """Which part of a long list a request asks for: limit items after skipping offset. A route
    that lists takes this, and answers through paged()."""

    def __init__(
        self,
        limit: Annotated[int | None, Query(ge=1, le=500)] = None,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit, self.offset = limit, offset


def paged[T](response: Response, found: tuple[list[T], int]) -> list[T]:
    """The part of a list that was asked for, with how many there are in all, whatever the
    limit, in X-Total-Count."""
    items, total = found
    response.headers["X-Total-Count"] = str(total)
    return items


def with_settings_checked(entry: SourceInput) -> SourceInput:
    """The source with its settings checked against its kind, defaults filled in."""
    return entry.model_copy(update={"settings": checked_settings(entry.kind, entry.settings)})


def create_app(
    database_url: str, collector_url: str | None = None, static_dir: str | None = None
) -> FastAPI:
    """collector_url: where the collector's API is, for testing sources; None when there is no
    collector to ask. static_dir: the built frontend to serve beside the API; None serves the
    API alone, as in development, where the frontend has its own server."""
    engine = create_engine(database_url, pool_pre_ping=True)
    storage = PostgresListings(engine, now=lambda: datetime.now(UTC), next_id=uuid4)
    collector = CollectorClient(collector_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            engine.dispose()

    # Operation ids are the route function names, so generated clients get readable calls.
    app = FastAPI(lifespan=lifespan, generate_unique_id_function=lambda route: route.name)

    @app.exception_handler(AliasConflict)
    @app.exception_handler(CapacityConflict)
    @app.exception_handler(IdempotencyConflict)
    async def save_conflict(
        request: Request, exc: IdempotencyConflict | CapacityConflict | AliasConflict
    ) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(CapacityRequired)
    async def capacity_required(request: Request, exc: CapacityRequired) -> JSONResponse:
        issue = {
            "type": "missing",
            "loc": ["body", "capacity_gb"],
            "msg": "Enter the capacity for a drive that has not been recorded yet.",
        }
        return JSONResponse(status_code=422, content={"detail": [issue]})

    @app.exception_handler(PriceRequired)
    async def price_required(request: Request, exc: PriceRequired) -> JSONResponse:
        issue = {
            "type": "missing",
            "loc": ["body", "item_price_cents"],
            "msg": "Enter the item price for an offer that has no price yet.",
        }
        return JSONResponse(status_code=422, content={"detail": [issue]})

    @app.exception_handler(UnknownStore)
    async def unknown_store(request: Request, exc: UnknownStore) -> JSONResponse:
        issue = {
            "type": "value_error",
            "loc": ["body", "store"],
            "msg": "Choose a known store.",
        }
        return JSONResponse(status_code=422, content={"detail": [issue]})

    @app.exception_handler(SettingsInvalid)
    async def settings_invalid(request: Request, exc: SettingsInvalid) -> JSONResponse:
        issues = [
            {"type": issue["type"], "loc": ["body", "settings", *issue["loc"]], "msg": issue["msg"]}
            for issue in exc.errors
        ]
        return JSONResponse(status_code=422, content={"detail": issues})

    @app.exception_handler(SourceExists)
    async def source_exists(request: Request, exc: SourceExists) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": f"A source named {exc} exists"})

    @app.exception_handler(CollectorUnavailable)
    async def no_collector(request: Request, exc: CollectorUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(SourceKept)
    async def source_kept(request: Request, exc: SourceKept) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(SourceNotFound)
    async def missing_source(request: Request, exc: SourceNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Source not found"})

    @app.exception_handler(ListingNotFound)
    async def missing_listing(request: Request, exc: ListingNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Listing not found"})

    @app.exception_handler(UnmatchedNotFound)
    async def missing_unmatched(request: Request, exc: UnmatchedNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Queued offer not found"})

    @app.exception_handler(DriveNotFound)
    async def missing_drive(request: Request, exc: DriveNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": "Drive not found"})

    @app.get("/api/listings", response_model=list[ListingSummary])
    def list_listings(store: StoreKey | None = None) -> list[dict[str, Any]]:
        return storage.list(store)

    @app.get("/api/price-history", response_model=list[Listing])
    def price_history(
        listing: Annotated[list[UUID] | None, Query()] = None,
    ) -> list[dict[str, Any]]:
        return storage.histories(listing or [])

    @app.post("/api/prices", status_code=201, response_model=Listing)
    def record_offer_price(
        entry: PriceInput, idempotency_key: Annotated[UUID, Header()]
    ) -> dict[str, Any]:
        return storage.record_price(entry, idempotency_key)

    @app.post(
        "/api/scraped",
        status_code=201,
        response_model=ScrapedResult,
        responses={
            202: {"model": ScrapedResult, "description": "Queued for review"},
            200: {"model": ScrapedResult, "description": "Ignored by an earlier decision"},
        },
    )
    def record_scraped(
        entry: ScrapedInput, idempotency_key: Annotated[UUID, Header()], response: Response
    ) -> dict[str, Any]:
        result = storage.record_scraped(entry, idempotency_key)
        response.status_code = {"recorded": 201, "queued": 202, "ignored": 200}[result["status"]]
        return result

    @app.post("/api/unmatched/{item_id}/resolve", response_model=Listing)
    def resolve_unmatched(item_id: UUID, resolution: Resolution) -> dict[str, Any]:
        return storage.resolve_unmatched(item_id, resolution)

    @app.post("/api/unmatched/{item_id}/ignore", status_code=204)
    def ignore_unmatched(item_id: UUID) -> None:
        storage.ignore_unmatched(item_id)

    @app.get("/api/unmatched", response_model=list[Unmatched])
    def list_unmatched(
        response: Response,
        paging: Annotated[Paging, Depends()],
        source: StoreKey | None = None,
        reason: UnmatchedReason | None = None,
    ) -> list[dict[str, Any]]:
        """The Review queue, newest first; by source and reason, and a part at a time, when
        asked. X-Total-Count says how many there are in all, whatever the limit."""
        return paged(response, storage.list_unmatched(source, reason, paging.limit, paging.offset))

    @app.get("/api/listings/{listing_id}", response_model=Listing)
    def get_listing(listing_id: UUID) -> dict[str, Any]:
        listing = storage.get(listing_id)
        if listing is None:
            raise HTTPException(404, "Listing not found")
        return listing

    @app.patch("/api/listings/{listing_id}", response_model=Listing)
    def edit_offer(listing_id: UUID, entry: OfferEdit) -> dict[str, Any]:
        return storage.edit_offer(listing_id, entry)

    @app.delete("/api/listings/{listing_id}", status_code=204)
    def delete_offer(listing_id: UUID) -> None:
        storage.delete_offer(listing_id)

    @app.delete(
        "/api/listings/{listing_id}/observations/{observation_id}",
        responses={
            200: {"model": Listing, "description": "The offer with its remaining prices"},
            204: {"description": "That was the offer's last price, so the offer is gone"},
        },
    )
    def delete_price(listing_id: UUID, observation_id: UUID) -> Response:
        remaining = storage.delete_price(listing_id, observation_id)
        return JSONResponse(remaining) if remaining is not None else Response(status_code=204)

    @app.get("/api/sources", response_model=list[SourceView])
    def list_sources() -> list[dict[str, Any]]:
        return storage.list_sources()

    @app.get("/api/sources/due", response_model=list[SourceView])
    def list_due_sources() -> list[dict[str, Any]]:
        # Only a collector asks, and only between runs: it is alive, and running nothing.
        storage.collector_idle()
        return storage.due_sources()

    @app.post("/api/sources/{source_id}/stop", status_code=202, response_model=SourceView)
    def request_source_stop(source_id: UUID) -> dict[str, Any]:
        return storage.request_stop(source_id)

    @app.post("/api/sources/{source_id}/run", status_code=202, response_model=SourceView)
    def request_source_run(source_id: UUID) -> dict[str, Any]:
        return storage.request_run(source_id)

    @app.get("/api/source-kinds", response_model=list[SourceKindView])
    def list_source_kinds() -> list[dict[str, Any]]:
        """The kinds of store there are, each as its reader describes it: what the Admin form
        asks for, and what a store's settings are checked against."""
        return [{"kind": kind, **described} for kind, described in KINDS.items()]

    @app.post("/api/sources", status_code=201, response_model=SourceView)
    def add_source(entry: SourceInput) -> dict[str, Any]:
        return storage.add_source(with_settings_checked(entry))

    @app.put("/api/sources/{source_id}", response_model=SourceView)
    def update_source(source_id: UUID, entry: SourceInput) -> dict[str, Any]:
        return storage.update_source(source_id, with_settings_checked(entry))

    @app.delete("/api/sources/{source_id}", status_code=204)
    def delete_source(source_id: UUID) -> None:
        storage.delete_source(source_id)

    def verdict_on(offer: dict[str, Any]) -> dict[str, str | None]:
        """What disktracker would do with an offer the collector read, were it recorded."""
        known = storage.drive_capacity(normalize_mpn(offer["mpn"])) if offer["mpn"] else None
        outcome, reason = preview_verdict(offer, known)
        return {"outcome": outcome, "reason": reason}

    @app.post("/api/source-previews", response_model=SourcePreview)
    def preview_source(entry: SourcePreviewInput) -> dict[str, Any]:
        """Try a source, saved or not: one offer as the collector reads it, and what recording
        it would do. Nothing is kept."""
        source = with_settings_checked(entry)
        preview = collector.preview(
            {
                "key": source_key(source.name),
                "kind": source.kind,
                "base_url": source.base_url,
                "transport": source.transport,
                "settings": source.settings,
                "conditions": storage.list_condition_rules(),
                "page_url": entry.page_url or None,
            }
        )
        offer = preview["offer"]
        return {**preview, "verdict": None if offer is None else verdict_on(offer)}

    @app.post("/api/source-inspections", response_model=SourceInspection)
    def inspect_link(entry: SourceInspectionInput) -> dict[str, Any]:
        """From a link to one product page of a store: the sources that would read the store,
        best first, each with the offer it reads from that page and what recording it would
        do. Nothing is kept."""
        inspected = collector.inspect(
            {
                "url": entry.url,
                "transport": entry.transport,
                "conditions": storage.list_condition_rules(),
            }
        )
        candidates = [
            {**candidate, "verdict": verdict_on(candidate["offer"])}
            for candidate in inspected["candidates"]
        ]
        return {**inspected, "candidates": candidates}

    @app.post("/api/listing-text", response_model=ListingFacts)
    def read_listing_text(entry: ListingText) -> dict[str, object]:
        conditions = condition_rules(
            (rule["pattern"], rule["condition"]) for rule in storage.list_condition_rules()
        )
        return read_listing(entry.text, conditions)._asdict()

    @app.get("/api/condition-rules", response_model=list[ConditionRule])
    def list_condition_rules() -> list[dict[str, Any]]:
        return storage.list_condition_rules()

    @app.put("/api/condition-rules", response_model=list[ConditionRule])
    def replace_condition_rules(rules: list[ConditionRule]) -> list[dict[str, Any]]:
        return storage.replace_condition_rules(rules)

    @app.post("/api/collector-runs", status_code=201, response_model=CollectorRun)
    def record_collector_run(run: CollectorRun) -> dict[str, Any]:
        return storage.record_run(run)

    @app.get("/api/collector-runs/latest", response_model=list[CollectorRun])
    def latest_collector_runs() -> list[dict[str, Any]]:
        return storage.latest_runs()

    @app.put("/api/collector-activity", response_model=ActivityAnswer)
    def report_collector_activity(progress: Activity) -> dict[str, bool]:
        return storage.report_activity(progress)

    @app.get("/api/collector-status", response_model=CollectorStatus)
    def collector_status() -> dict[str, Any]:
        return storage.collector_status()

    @app.post("/api/drives/{drive_id}/aliases", status_code=201, response_model=Drive)
    def add_alias(drive_id: UUID, entry: AliasInput) -> dict[str, Any]:
        return storage.add_alias(drive_id, entry.mpn)

    @app.put("/api/drives/{drive_id}/specifications", response_model=Drive)
    def replace_specifications(drive_id: UUID, entry: DriveSpecifications) -> dict[str, Any]:
        return storage.replace_specifications(drive_id, entry)

    if static_dir is not None:
        site = Path(static_dir).resolve()

        @app.get("/{path:path}", include_in_schema=False)
        def page(path: str) -> FileResponse:
            """A file of the built frontend; any other path that is not a file's is a route
            inside the app, so it gets the app's page."""
            asked = (site / path).resolve()
            if asked.is_file() and asked.is_relative_to(site):
                return FileResponse(asked)
            if path.startswith("api/") or Path(path).suffix:
                raise HTTPException(status_code=404)
            return FileResponse(site / "index.html")

    return app
