"""Posts scraped offers to disktracker, which records them or queues them for review.

Wraps the client generated from disktracker's OpenAPI spec (disktracker_api), adding retries
with a stable idempotency key and turning every failure into the collector's own errors."""

import logging
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from typing import Any, TypeVar, cast
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from listing_text.readers import ConditionRules, condition_rules

from collector.clock import Clock
from collector.errors import DisktrackerUnavailable
from collector.models import Posted, RunSummary, ScrapedOffer
from disktracker_api import Client
from disktracker_api.api.default import (
    list_condition_rules,
    list_due_sources,
    list_listings,
    record_collector_run,
    record_scraped,
    report_collector_activity,
)
from disktracker_api.models import (
    Activity,
    ActivityAnswer,
    CollectorRun,
    ConditionRule,
    HTTPValidationError,
    ListingSummary,
    ScrapedInput,
    ScrapedResult,
    SourceView,
)
from disktracker_api.types import Response

log = logging.getLogger(__name__)
ATTEMPTS = 3
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


class DisktrackerClient:
    def __init__(self, api: Client, retry_delay: float, clock: Clock) -> None:
        self.api, self.retry_delay, self.clock = api, retry_delay, clock

    def due_sources(self) -> list[SourceView]:
        return _read_list("sources", lambda: list_due_sources.sync_detailed(client=self.api))

    def condition_rules(self) -> ConditionRules:
        rules: list[ConditionRule] = _read_list(
            "condition rules", lambda: list_condition_rules.sync_detailed(client=self.api)
        )
        return condition_rules((rule.pattern, rule.condition) for rule in rules)

    def listings(self, store: str) -> list[ListingSummary]:
        return _read_list(
            "listings", lambda: list_listings.sync_detailed(client=self.api, store=store)
        )

    def post_scraped(self, offer: ScrapedOffer, observed_at: datetime) -> Posted:
        # The same key on every attempt lets disktracker replay a save whose response was lost.
        key = uuid5(NAMESPACE_URL, f"{offer.source}|{offer.url}|{observed_at.isoformat()}")
        # openapi-python-client 0.29.1 puts header values into the request unconverted, and
        # httpx only accepts str headers, so the key goes in as its string form.
        header_key = cast(UUID, str(key))
        body = ScrapedInput.from_dict(offer.payload(observed_at))
        for attempt in range(1, ATTEMPTS + 1):
            try:
                response = record_scraped.sync_detailed(
                    client=self.api, body=body, idempotency_key=header_key
                )
            except (httpx.HTTPError, ValueError) as error:
                failure: dict[str, object] = {"status": None, "detail": str(error)}
            else:
                if isinstance(response.parsed, ScrapedResult):
                    listing_id = response.parsed.listing_id
                    log.debug(
                        "offer_posted", extra={"url": offer.url, "status": response.parsed.status}
                    )
                    return Posted(
                        response.parsed.status, listing_id if isinstance(listing_id, UUID) else None
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

    def report_progress(self, source: str, started_at: datetime, counts: dict[str, int]) -> bool:
        """Tell disktracker how far a run has got, once: the next report says it again."""
        body = Activity.from_dict(
            {"source": source, "started_at": started_at.isoformat(), **counts}
        )
        try:
            response = report_collector_activity.sync_detailed(client=self.api, body=body)
        except (httpx.HTTPError, ValueError, KeyError) as error:
            raise DisktrackerUnavailable(str(error)) from error
        if not isinstance(response.parsed, ActivityAnswer):
            raise DisktrackerUnavailable(f"progress: HTTP {response.status_code}")
        return response.parsed.stop

    def report_run(self, summary: RunSummary, started_at: datetime, finished_at: datetime) -> None:
        """Tell disktracker how a run went, once: a lost report only leaves the admin
        overview a run behind."""
        body = CollectorRun.from_dict(
            {
                **asdict(summary),
                "started_at": started_at.isoformat(),
                "finished_at": finished_at.isoformat(),
            }
        )
        try:
            response = record_collector_run.sync_detailed(client=self.api, body=body)
        except (httpx.HTTPError, ValueError) as error:
            raise DisktrackerUnavailable(str(error)) from error
        if not isinstance(response.parsed, CollectorRun):
            raise DisktrackerUnavailable(f"runs: HTTP {response.status_code}")


def detail(parsed: object, content: bytes) -> object:
    """What disktracker said about a rejected post: its validation errors, or the raw reply."""
    if isinstance(parsed, HTTPValidationError):
        return parsed.to_dict()["detail"]
    return content.decode(errors="replace")
