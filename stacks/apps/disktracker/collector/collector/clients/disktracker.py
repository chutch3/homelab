"""Posts scraped offers to disktracker, which records them or queues them for review.

Wraps the client generated from disktracker's OpenAPI spec (disktracker_api), adding retries
with a stable idempotency key and turning every failure into the collector's own errors."""

import logging
from collections.abc import Callable, Sequence
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from typing import Any, TypeVar, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from listing_text.readers import ConditionRules, condition_rules

from collector.clock import Clock
from collector.errors import DisktrackerUnavailable
from collector.models import Posted, RunSummary, ScrapedOffer, SourceView
from disktracker_api import Client
from disktracker_api.api.collection import heartbeat, start_run, update_run
from disktracker_api.api.listing_tools import list_condition_rules
from disktracker_api.api.offers import list_offers
from disktracker_api.api.prices import ingest, record_price
from disktracker_api.models import (
    ConditionRule,
    Heartbeat,
    HeartbeatAnswer,
    HTTPValidationError,
    IngestionInput,
    ManualSourceView,
    OfferSummary,
    PriceInput,
    PriceResult,
    Run,
    RunStart,
    RunUpdate,
    SapCommerceSourceView,
    ShopifySourceView,
    SitemapSourceView,
)
from disktracker_api.types import Response

# Each kind of source, as disktracker describes it.
VIEWS: dict[str, type[SourceView]] = {
    "manual": ManualSourceView,
    "shopify": ShopifySourceView,
    "sitemap": SitemapSourceView,
    "sap_commerce": SapCommerceSourceView,
}

log = logging.getLogger(__name__)
ATTEMPTS = 3
# What a run summary says that is not a count.
NOT_COUNTS = ("source", "completed", "stopped", "reason")
# The longest reason disktracker keeps for a run.
REASON_LIMIT = 500
T = TypeVar("T")


def _read_list(what: str, call: Callable[[], Response[Any]]) -> list[T]:
    """What disktracker lists; an answer the collector cannot read (a disktracker of another
    version) is disktracker being unavailable, not a crash."""
    try:
        response = call()
    except KeyError as error:
        raise DisktrackerUnavailable(f"{what}: the answer has no {error.args[0]}") from error
    except (httpx.HTTPError, ValueError, TypeError) as error:
        raise DisktrackerUnavailable(str(error)) from error
    if not isinstance(response.parsed, list):
        raise DisktrackerUnavailable(f"{what}: HTTP {response.status_code}")
    return cast(list[T], response.parsed)


def source_of(item: dict[str, Any]) -> SourceView:
    view = VIEWS.get(item["kind"])
    if view is None:
        raise ValueError(f"sources: a {item['kind']} source is of no kind this collector reads")
    return view.from_dict(item)


class DisktrackerClient:
    def __init__(self, api: Client, retry_delay: float, clock: Clock) -> None:
        self.api, self.retry_delay, self.clock = api, retry_delay, clock

    def due_sources(self) -> list[SourceView]:
        return _read_list("sources", self._due)

    def _due(self) -> Response[Any]:
        """The due sources, each read as its own kind. The generated client tries every kind
        in turn and says only what the last one found wrong; read by kind, what is wrong with
        a source (a field it lacks) is said by name."""
        answer = self.api.get_httpx_client().get("/api/sources", params={"due": True})
        parsed = [source_of(item) for item in answer.json()] if answer.is_success else None
        return Response(HTTPStatus(answer.status_code), answer.content, answer.headers, parsed)

    def condition_rules(self) -> ConditionRules:
        rules: list[ConditionRule] = _read_list(
            "condition rules", lambda: list_condition_rules.sync_detailed(client=self.api)
        )
        return condition_rules((rule.pattern, rule.condition) for rule in rules)

    def known_offers(self, store: str) -> list[OfferSummary]:
        return _read_list("offers", lambda: list_offers.sync_detailed(client=self.api, store=store))

    def post_scraped(self, offer: ScrapedOffer, observed_at: datetime) -> Posted:
        # The same key on every attempt lets disktracker replay a save whose response was lost.
        key = uuid5(NAMESPACE_URL, f"{offer.source}|{offer.url}|{observed_at.isoformat()}")
        # openapi-python-client 0.29.1 puts header values into the request unconverted, and
        # httpx only accepts str headers, so the key goes in as its string form.
        header_key = cast(UUID, str(key))
        payload = offer.payload(observed_at)

        def send() -> Response[Any]:
            # A page read afresh is taken in; a recheck of an offer disktracker knows is only a
            # price of it, and gives no new evidence of what the page is.
            if offer.offer_id is None:
                return ingest.sync_detailed(
                    client=self.api, body=IngestionInput.from_dict(payload),
                    idempotency_key=header_key,
                )  # fmt: skip
            return record_price.sync_detailed(
                client=self.api, body=PriceInput.from_dict(payload), idempotency_key=header_key
            )

        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = send()
            except (httpx.HTTPError, ValueError) as error:
                failure: dict[str, object] = {"status": None, "detail": str(error)}
            else:
                if isinstance(response.parsed, PriceResult):
                    offer_id = response.parsed.offer_id
                    log.debug(
                        "offer_posted", extra={"url": offer.url, "status": response.parsed.status}
                    )
                    return Posted(
                        response.parsed.status, offer_id if isinstance(offer_id, UUID) else None
                    )
                failure = {
                    "status": int(response.status_code),
                    "detail": detail(response.parsed, response.content),
                }
                if response.status_code < 500:
                    break
            if attempt < ATTEMPTS:
                self.clock.sleep(self.retry_delay * attempt)
        log.warning("post_failed", extra={"url": offer.url, **failure})
        return Posted("failed")

    def heartbeat(self, runs: Sequence[UUID]) -> None:
        """Say the collector is alive, with the runs it has (none between runs), once."""
        try:
            response = heartbeat.sync_detailed(
                client=self.api,
                body=Heartbeat(runs=list(runs)),
            )
        except (httpx.HTTPError, ValueError) as error:
            raise DisktrackerUnavailable(str(error)) from error
        if not isinstance(response.parsed, HeartbeatAnswer):
            raise DisktrackerUnavailable(f"heartbeat: HTTP {response.status_code}")

    def start_run(self, run_id: UUID, source: str, started_at: datetime) -> None:
        """Register a run as it starts. The run's id makes it safe to ask again: a start whose
        answer was lost is answered the same the next time."""
        body = RunStart(id=run_id, source=source, started_at=started_at)
        self._run_call(lambda: start_run.sync_detailed(client=self.api, body=body))

    def report_progress(self, run_id: UUID, counts: dict[str, int]) -> bool:
        """Tell disktracker how far a run has got, once: the next report says it again.
        Whether the run has been asked to stop."""
        body = RunUpdate.from_dict(counts)
        try:
            response = update_run.sync_detailed(run_id, client=self.api, body=body)
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise DisktrackerUnavailable(str(error)) from error
        if not isinstance(response.parsed, Run):
            raise DisktrackerUnavailable(f"progress: HTTP {response.status_code}")
        return response.parsed.stop_requested

    def finish_run(self, run_id: UUID, summary: RunSummary, finished_at: datetime) -> None:
        """Tell disktracker how a run ended: completed, stopped, or failed. The same end may be
        sent again until it is taken."""
        counts = {key: value for key, value in asdict(summary).items() if key not in NOT_COUNTS}
        status = "completed" if summary.completed else "stopped" if summary.stopped else "failed"
        # Only a failed run says why, in as much as disktracker keeps.
        why = (
            {"reason": summary.reason[:REASON_LIMIT]}
            if status == "failed" and summary.reason
            else {}
        )
        body = RunUpdate.from_dict(
            {**counts, "status": status, "finished_at": finished_at.isoformat(), **why}
        )
        self._run_call(lambda: update_run.sync_detailed(run_id, client=self.api, body=body))

    def _run_call(self, call: Callable[[], Response[Any]]) -> None:
        """A call about a run, tried again on a failure that may pass (no answer, or a server
        error): the run's id makes each attempt the same request."""
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = call()
            except (httpx.HTTPError, ValueError) as error:
                failure = str(error)
            else:
                if isinstance(response.parsed, Run):
                    return
                failure = f"runs: HTTP {response.status_code}"
                if response.status_code < 500:
                    break
            if attempt < ATTEMPTS:
                self.clock.sleep(self.retry_delay * attempt)
        raise DisktrackerUnavailable(failure)


def detail(parsed: object, content: bytes) -> object:
    """What disktracker said about a rejected post: its validation errors, or the raw reply."""
    if isinstance(parsed, HTTPValidationError):
        return parsed.to_dict()["detail"]
    return content.decode(errors="replace")
