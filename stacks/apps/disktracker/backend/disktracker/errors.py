"""What can go wrong in a workflow, and how each is answered over HTTP."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import Field

from disktracker.collection.client import CollectorUnavailable
from disktracker.collection.settings import KINDS
from disktracker.contract import Contract


class ErrorResponse(Contract):
    """A failed operation. Validation errors instead return a list of field issues in detail."""

    detail: str = Field(description="Why the operation could not be completed.")


class CapacityRequired(Exception):
    """A drive not recorded yet needs its capacity."""


class CapacityConflict(Exception):
    """The capacity given is not the drive's; the message says what it is."""


class PriceRequired(Exception):
    """An offer with no price yet needs one."""


class IdempotencyConflict(Exception):
    pass


class DecisionConflict(Exception):
    pass


class OfferNotFound(Exception):
    pass


class DriveNotFound(Exception):
    pass


class UnknownStore(Exception):
    pass


class SourceExists(Exception):
    pass


class SourceNotFound(Exception):
    pass


class SourceKept(Exception):
    """The source cannot be deleted; the message says why."""


class AliasConflict(Exception):
    pass


class ReviewItemNotFound(Exception):
    pass


class RunNotFound(Exception):
    pass


class RunConflict(Exception):
    """A run cannot become what was asked; the message says why."""


class UnknownSource(Exception):
    pass


def _missing(field: str, message: str) -> JSONResponse:
    issue = {"type": "missing", "loc": ["body", field], "msg": message}
    return JSONResponse(status_code=422, content={"detail": [issue]})


# What a body is checked as, chosen by one of its fields: a source by its kind, a review decision
# by what it decides.
TAGS = {*KINDS, "match", "ignore"}


# A store's settings are entered in the Admin form, which shows each issue beside its setting:
# in the form's words, by what was wrong.
SETTING_ISSUES = {
    "missing": "Enter this.",
    "string_too_short": "Enter this.",
    "too_short": "Enter at least one.",
    "string_type": "Enter text.",
    "list_type": "Enter a list.",
    "bool_parsing": "Choose yes or no.",
    "bool_type": "Choose yes or no.",
}


def worded(issue: dict[str, Any]) -> dict[str, Any]:
    """A setting's issue in the form's words: a rule's own sentence, or what was wrong."""
    if tuple(issue["loc"][:2]) != ("body", "settings"):
        return issue
    if issue["type"] == "value_error":
        return {**issue, "msg": str(issue["ctx"]["error"])}
    return {**issue, "msg": SETTING_ISSUES.get(issue["type"], issue["msg"])}


def located(issue: dict[str, Any]) -> dict[str, Any]:
    """A validation issue, where the form shows it. A body checked as what one of its fields
    chooses is not checked as that choice for where an issue is; a choice there is none of is
    that field's."""
    loc = tuple(issue["loc"])
    if issue["type"] in ("union_tag_invalid", "union_tag_not_found"):
        field = str(issue.get("ctx", {}).get("discriminator", "'kind'")).strip("'")
        return {**issue, "loc": (*loc, field)} | (
            {"msg": "Choose a type."} if field == "kind" else {}
        )
    if len(loc) > 1 and loc[0] == "body" and loc[1] in TAGS:
        return {**issue, "loc": (loc[0], *loc[2:])}
    return issue


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AliasConflict)
    @app.exception_handler(CapacityConflict)
    @app.exception_handler(IdempotencyConflict)
    @app.exception_handler(DecisionConflict)
    @app.exception_handler(SourceKept)
    @app.exception_handler(RunConflict)
    async def conflict(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(CapacityRequired)
    async def capacity_required(request: Request, exc: CapacityRequired) -> JSONResponse:
        return _missing(
            "capacity_gb", "Enter the capacity for a drive that has not been recorded yet."
        )

    @app.exception_handler(PriceRequired)
    async def price_required(request: Request, exc: PriceRequired) -> JSONResponse:
        return _missing(
            "item_price_cents", "Enter the item price for an offer that has no price yet."
        )

    @app.exception_handler(UnknownStore)
    async def unknown_store(request: Request, exc: UnknownStore) -> JSONResponse:
        issue = {"type": "value_error", "loc": ["body", "store"], "msg": "Choose a known store."}
        return JSONResponse(status_code=422, content={"detail": [issue]})

    @app.exception_handler(UnknownSource)
    async def unknown_source(request: Request, exc: UnknownSource) -> JSONResponse:
        issue = {"type": "value_error", "loc": ["body", "source"], "msg": "Choose a known source."}
        return JSONResponse(status_code=422, content={"detail": [issue]})

    @app.exception_handler(RequestValidationError)
    async def invalid(request: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "detail": jsonable_encoder([worded(located(issue)) for issue in exc.errors()])
            },
        )

    @app.exception_handler(SourceExists)
    async def source_exists(request: Request, exc: SourceExists) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": f"A source named {exc} exists"})

    @app.exception_handler(CollectorUnavailable)
    async def no_collector(request: Request, exc: CollectorUnavailable) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    def missing(kind: type[Exception], detail: str) -> None:
        @app.exception_handler(kind)
        async def not_found(request: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(status_code=404, content={"detail": detail})

    missing(SourceNotFound, "Source not found")
    missing(OfferNotFound, "Offer not found")
    missing(ReviewItemNotFound, "Review item not found")
    missing(DriveNotFound, "Drive not found")
    missing(RunNotFound, "Run not found")
