"""Collection over HTTP: the stores offers are collected from, the runs collecting them, what
the collector says while it runs, and trying a store before it is collected."""

from typing import Annotated, Any
from uuid import UUID

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, Query, Response

from disktracker.collection.schemas import (
    CollectorStatus,
    Heartbeat,
    HeartbeatAnswer,
    Run,
    RunQuery,
    RunStart,
    RunUpdate,
    SourceInput,
    SourceInspection,
    SourceInspectionInput,
    SourceKindView,
    SourcePreview,
    SourcePreviewInput,
    SourceQuery,
    SourceView,
)
from disktracker.collection.service import CollectionService
from disktracker.collection.settings import KINDS
from disktracker.container import Container
from disktracker.http_errors import ErrorResponse

router = APIRouter(prefix="/api")


Collection = Annotated[CollectionService, Depends(Provide[Container.collection_service])]


@router.get(
    "/sources",
    response_model=list[SourceView],
    tags=["Sources"],
    summary="List configured or due sources",
)
@inject
def list_sources(
    collection: Collection, query: Annotated[SourceQuery, Query()]
) -> list[dict[str, Any]]:
    """Every source by name; with due, only those due to run now, in the order to run them.
    Reading changes nothing."""
    return collection.due_sources() if query.due else collection.list_sources()


@router.post(
    "/sources/{source_id}/stop",
    status_code=202,
    response_model=SourceView,
    tags=["Sources"],
    summary="Request that a source stop collecting",
    responses={404: {"model": ErrorResponse, "description": "Source not found"}},
)
@inject
def request_source_stop(collection: Collection, source_id: UUID) -> dict[str, Any]:
    """Request cooperative cancellation. A 202 response acknowledges the request; the collector
    stops when it next reports progress and sees stop_requested."""
    return collection.request_stop(source_id)


@router.post(
    "/sources/{source_id}/run",
    status_code=202,
    response_model=SourceView,
    tags=["Sources"],
    summary="Schedule a source to run now",
    responses={404: {"model": ErrorResponse, "description": "Source not found"}},
)
@inject
def request_source_run(collection: Collection, source_id: UUID) -> dict[str, Any]:
    """Make the source due now until a collector registers its run. A 202 response acknowledges
    scheduling; collection has not necessarily started."""
    return collection.request_run(source_id)


@router.get(
    "/source-kinds",
    response_model=list[SourceKindView],
    tags=["Sources"],
    summary="List reader kinds and their settings",
)
def list_source_kinds() -> list[dict[str, Any]]:
    """The kinds of store there are, each as its settings model describes it: what the Admin
    form asks for, and what a store's settings are checked against."""
    return [{"kind": name, **kind.described()} for name, kind in KINDS.items()]


@router.post(
    "/sources",
    status_code=201,
    response_model=SourceView,
    tags=["Sources"],
    summary="Create a source",
    responses={
        409: {"model": ErrorResponse, "description": "A source with this name already exists"}
    },
)
@inject
def add_source(collection: Collection, entry: SourceInput) -> dict[str, Any]:
    """Create a store configuration. Its stable string key is derived from its name; prices and
    runs use that key, while source-management paths use its UUID. GET /api/source-kinds
    describes accepted kinds and settings."""
    return collection.add_source(entry)


@router.put(
    "/sources/{source_id}",
    response_model=SourceView,
    tags=["Sources"],
    summary="Replace source configuration",
    responses={
        404: {"model": ErrorResponse, "description": "Source not found"},
        409: {"model": ErrorResponse, "description": "A source with this name already exists"},
    },
)
@inject
def update_source(collection: Collection, source_id: UUID, entry: SourceInput) -> dict[str, Any]:
    """Replace the source configuration; omitted optional fields take their defaults. Renaming
    preserves the source key used by prices and runs."""
    return collection.update_source(source_id, entry)


@router.delete(
    "/sources/{source_id}",
    status_code=204,
    tags=["Sources"],
    summary="Delete an unused source",
    responses={
        404: {"model": ErrorResponse, "description": "Source not found"},
        409: {
            "model": ErrorResponse,
            "description": "The source has offers or review items, or is the reserved Other source",
        },
    },
)
@inject
def delete_source(collection: Collection, source_id: UUID) -> None:
    """Delete a source with no offers or review items, along with its runs and review decisions.
    The reserved Other source cannot be deleted. Disable a source that still has offers."""
    collection.delete_source(source_id)


@router.post(
    "/source-previews",
    response_model=SourcePreview,
    tags=["Sources"],
    summary="Preview a source without saving it",
    responses={503: {"model": ErrorResponse, "description": "The collector is unavailable"}},
)
@inject
def preview_source(collection: Collection, entry: SourcePreviewInput) -> dict[str, Any]:
    """Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept."""
    return collection.preview_source(entry)


@router.post(
    "/source-inspections",
    response_model=SourceInspection,
    tags=["Sources"],
    summary="Find readers for a store product page",
    responses={503: {"model": ErrorResponse, "description": "The collector is unavailable"}},
)
@inject
def inspect_link(collection: Collection, entry: SourceInspectionInput) -> dict[str, Any]:
    """From a link to one product page of a store: the sources that would read the store,
    best first, each with the offer it reads from that page and what recording it would
    do. Nothing is kept."""
    return collection.inspect_link(entry)


@router.post(
    "/collection-runs",
    status_code=201,
    response_model=Run,
    responses={
        200: {"model": Run, "description": "Already registered: the run as it is"},
        409: {"model": ErrorResponse, "description": "The run id was used for a different start"},
    },
    tags=["Collection"],
    summary="Register a collection run",
)
@inject
def start_run(collection: Collection, start: RunStart, response: Response) -> dict[str, Any]:
    """Register a run as it starts, under the id the collector chose: the same start sent again
    is answered with the run (200), and another under its id is refused (409). A run of the
    source still marked running is abandoned."""
    run, created = collection.start_run(start)
    if not created:
        response.status_code = 200
    return run


@router.patch(
    "/collection-runs/{run_id}",
    response_model=Run,
    tags=["Collection"],
    summary="Report progress or finish a collection run",
    responses={
        404: {"model": ErrorResponse, "description": "Run not found"},
        409: {
            "model": ErrorResponse,
            "description": "The run already ended with different results",
        },
    },
)
@inject
def update_run(collection: Collection, run_id: UUID, update: RunUpdate) -> dict[str, Any]:
    """How far a run has got, or how it ended. The answer's stop_requested says whether it
    should end here. A run that has ended stays as it ended: the same end again is answered as
    before, and anything else is refused (409)."""
    return collection.update_run(run_id, update)


@router.get(
    "/collection-runs",
    response_model=list[Run],
    tags=["Collection"],
    summary="List collection runs",
)
@inject
def list_runs(collection: Collection, query: Annotated[RunQuery, Query()]) -> list[dict[str, Any]]:
    """Return runs oldest first, filtered by source key, status and finished_since. With
    latest_per_source=true, return the latest matching run of each source, ordered by source
    key. This list is not paginated."""
    return collection.runs(query)


@router.put(
    "/collector-heartbeat",
    response_model=HeartbeatAnswer,
    tags=["Collection"],
    summary="Report the collector heartbeat and owned runs",
)
@inject
def heartbeat(collection: Collection, beat: Heartbeat) -> dict[str, Any]:
    """The collector is alive, whether it has runs or not: it names the runs it has, and any
    other still marked running is abandoned."""
    return collection.heartbeat(beat)


@router.get(
    "/collector-status",
    response_model=CollectorStatus,
    tags=["Collection"],
    summary="Get collector activity and waiting sources",
)
@inject
def collector_status(collection: Collection) -> dict[str, Any]:
    """Return the last heartbeat, active runs and source keys waiting to run in scheduling order.
    seen_at is null when the collector has never been heard from."""
    return collection.collector_status()
