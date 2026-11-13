from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.ingestion_input import IngestionInput
from ...models.price_result import PriceResult
from typing import cast
from uuid import UUID



def _get_kwargs(
    *,
    body: IngestionInput,
    idempotency_key: UUID,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["idempotency-key"] = idempotency_key







    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/ingestions",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | PriceResult | None:
    if response.status_code == 200:
        response_200 = PriceResult.from_dict(response.json())



        return response_200

    if response.status_code == 201:
        response_201 = PriceResult.from_dict(response.json())



        return response_201

    if response.status_code == 202:
        response_202 = PriceResult.from_dict(response.json())



        return response_202

    if response.status_code == 409:
        response_409 = ErrorResponse.from_dict(response.json())



        return response_409

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | PriceResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: IngestionInput,
    idempotency_key: UUID,

) -> Response[ErrorResponse | HTTPValidationError | PriceResult]:
    """ Take in a collected store page

     Take in one observation of a store page as collected: match it to a drive (registering
    one new under a known MPN and capacity), record its price, or queue it for review when it
    cannot be matched or is in doubt, or ignore it as an earlier review decided. One
    observation, one outcome: the Idempotency-Key answers it again as it was the first time,
    without doing the work again, and refuses a different body (409).

    A price of an offer already known by id, a recheck among them, goes to POST /prices: it
    gives no new evidence of what the page is.

    Args:
        idempotency_key (UUID): New UUID for each observation. Retry using the same key and body;
            changing the body returns 409.
        body (IngestionInput): One observation of a store page as a collector read it: the offer
            described, never named,
            by its store, the MPN and condition the page gives (either may be missing) and, for a one-
            off
            store, its seller. One that cannot be matched to a drive waits for review, which shows the
            reviewer its page and title.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | PriceResult]
     """


    kwargs = _get_kwargs(
        body=body,
idempotency_key=idempotency_key,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    body: IngestionInput,
    idempotency_key: UUID,

) -> ErrorResponse | HTTPValidationError | PriceResult | None:
    """ Take in a collected store page

     Take in one observation of a store page as collected: match it to a drive (registering
    one new under a known MPN and capacity), record its price, or queue it for review when it
    cannot be matched or is in doubt, or ignore it as an earlier review decided. One
    observation, one outcome: the Idempotency-Key answers it again as it was the first time,
    without doing the work again, and refuses a different body (409).

    A price of an offer already known by id, a recheck among them, goes to POST /prices: it
    gives no new evidence of what the page is.

    Args:
        idempotency_key (UUID): New UUID for each observation. Retry using the same key and body;
            changing the body returns 409.
        body (IngestionInput): One observation of a store page as a collector read it: the offer
            described, never named,
            by its store, the MPN and condition the page gives (either may be missing) and, for a one-
            off
            store, its seller. One that cannot be matched to a drive waits for review, which shows the
            reviewer its page and title.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | PriceResult
     """


    return sync_detailed(
        client=client,
body=body,
idempotency_key=idempotency_key,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: IngestionInput,
    idempotency_key: UUID,

) -> Response[ErrorResponse | HTTPValidationError | PriceResult]:
    """ Take in a collected store page

     Take in one observation of a store page as collected: match it to a drive (registering
    one new under a known MPN and capacity), record its price, or queue it for review when it
    cannot be matched or is in doubt, or ignore it as an earlier review decided. One
    observation, one outcome: the Idempotency-Key answers it again as it was the first time,
    without doing the work again, and refuses a different body (409).

    A price of an offer already known by id, a recheck among them, goes to POST /prices: it
    gives no new evidence of what the page is.

    Args:
        idempotency_key (UUID): New UUID for each observation. Retry using the same key and body;
            changing the body returns 409.
        body (IngestionInput): One observation of a store page as a collector read it: the offer
            described, never named,
            by its store, the MPN and condition the page gives (either may be missing) and, for a one-
            off
            store, its seller. One that cannot be matched to a drive waits for review, which shows the
            reviewer its page and title.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | PriceResult]
     """


    kwargs = _get_kwargs(
        body=body,
idempotency_key=idempotency_key,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: IngestionInput,
    idempotency_key: UUID,

) -> ErrorResponse | HTTPValidationError | PriceResult | None:
    """ Take in a collected store page

     Take in one observation of a store page as collected: match it to a drive (registering
    one new under a known MPN and capacity), record its price, or queue it for review when it
    cannot be matched or is in doubt, or ignore it as an earlier review decided. One
    observation, one outcome: the Idempotency-Key answers it again as it was the first time,
    without doing the work again, and refuses a different body (409).

    A price of an offer already known by id, a recheck among them, goes to POST /prices: it
    gives no new evidence of what the page is.

    Args:
        idempotency_key (UUID): New UUID for each observation. Retry using the same key and body;
            changing the body returns 409.
        body (IngestionInput): One observation of a store page as a collector read it: the offer
            described, never named,
            by its store, the MPN and condition the page gives (either may be missing) and, for a one-
            off
            store, its seller. One that cannot be matched to a drive waits for review, which shows the
            reviewer its page and title.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | PriceResult
     """


    return (await asyncio_detailed(
        client=client,
body=body,
idempotency_key=idempotency_key,

    )).parsed
