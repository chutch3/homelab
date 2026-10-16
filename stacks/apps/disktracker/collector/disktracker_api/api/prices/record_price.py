from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.price_input import PriceInput
from ...models.price_result import PriceResult
from typing import cast
from uuid import UUID



def _get_kwargs(
    *,
    body: PriceInput,
    idempotency_key: UUID,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["idempotency-key"] = idempotency_key







    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/prices",
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

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())



        return response_404

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
    body: PriceInput,
    idempotency_key: UUID,

) -> Response[ErrorResponse | HTTPValidationError | PriceResult]:
    """ Record a manual or collected price

     Record a price, whoever submits it. The Idempotency-Key names the submission: sent again
    with the same body it is answered as it was the first time, without doing the work again;
    sent with a different body it is refused (409).

    Either name offer_id (omit store, MPN and condition), or describe the offer with store,
    MPN and condition. Store `other` also requires seller. A new drive needs capacity_gb.
    With on_unmatched=queue, MPN and condition may be absent, but title and URL are required.
    An in-stock observation needs a positive item price. An out-of-stock observation without
    a price reuses the last price; a manual entry cannot do this for an offer never priced.
    Collected observations also honor saved review decisions and ignore never-priced sold-out
    offers. provenance defaults to manual and on_unmatched defaults to reject.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price, from a person or a collector alike. The offer it is
            for is either
            named (offer_id) or described: its store, MPN, condition and, for a one-off store, seller.

            on_unmatched says what to do with a described offer that cannot be matched to a drive (its
            MPN or condition is unknown, its drive's capacity is unknown, or its capacity disagrees
            with
            the drive's): reject refuses the price; queue keeps it for review, which needs the page
            and
            title a reviewer is shown.

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
    body: PriceInput,
    idempotency_key: UUID,

) -> ErrorResponse | HTTPValidationError | PriceResult | None:
    """ Record a manual or collected price

     Record a price, whoever submits it. The Idempotency-Key names the submission: sent again
    with the same body it is answered as it was the first time, without doing the work again;
    sent with a different body it is refused (409).

    Either name offer_id (omit store, MPN and condition), or describe the offer with store,
    MPN and condition. Store `other` also requires seller. A new drive needs capacity_gb.
    With on_unmatched=queue, MPN and condition may be absent, but title and URL are required.
    An in-stock observation needs a positive item price. An out-of-stock observation without
    a price reuses the last price; a manual entry cannot do this for an offer never priced.
    Collected observations also honor saved review decisions and ignore never-priced sold-out
    offers. provenance defaults to manual and on_unmatched defaults to reject.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price, from a person or a collector alike. The offer it is
            for is either
            named (offer_id) or described: its store, MPN, condition and, for a one-off store, seller.

            on_unmatched says what to do with a described offer that cannot be matched to a drive (its
            MPN or condition is unknown, its drive's capacity is unknown, or its capacity disagrees
            with
            the drive's): reject refuses the price; queue keeps it for review, which needs the page
            and
            title a reviewer is shown.

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
    body: PriceInput,
    idempotency_key: UUID,

) -> Response[ErrorResponse | HTTPValidationError | PriceResult]:
    """ Record a manual or collected price

     Record a price, whoever submits it. The Idempotency-Key names the submission: sent again
    with the same body it is answered as it was the first time, without doing the work again;
    sent with a different body it is refused (409).

    Either name offer_id (omit store, MPN and condition), or describe the offer with store,
    MPN and condition. Store `other` also requires seller. A new drive needs capacity_gb.
    With on_unmatched=queue, MPN and condition may be absent, but title and URL are required.
    An in-stock observation needs a positive item price. An out-of-stock observation without
    a price reuses the last price; a manual entry cannot do this for an offer never priced.
    Collected observations also honor saved review decisions and ignore never-priced sold-out
    offers. provenance defaults to manual and on_unmatched defaults to reject.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price, from a person or a collector alike. The offer it is
            for is either
            named (offer_id) or described: its store, MPN, condition and, for a one-off store, seller.

            on_unmatched says what to do with a described offer that cannot be matched to a drive (its
            MPN or condition is unknown, its drive's capacity is unknown, or its capacity disagrees
            with
            the drive's): reject refuses the price; queue keeps it for review, which needs the page
            and
            title a reviewer is shown.

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
    body: PriceInput,
    idempotency_key: UUID,

) -> ErrorResponse | HTTPValidationError | PriceResult | None:
    """ Record a manual or collected price

     Record a price, whoever submits it. The Idempotency-Key names the submission: sent again
    with the same body it is answered as it was the first time, without doing the work again;
    sent with a different body it is refused (409).

    Either name offer_id (omit store, MPN and condition), or describe the offer with store,
    MPN and condition. Store `other` also requires seller. A new drive needs capacity_gb.
    With on_unmatched=queue, MPN and condition may be absent, but title and URL are required.
    An in-stock observation needs a positive item price. An out-of-stock observation without
    a price reuses the last price; a manual entry cannot do this for an offer never priced.
    Collected observations also honor saved review decisions and ignore never-priced sold-out
    offers. provenance defaults to manual and on_unmatched defaults to reject.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price, from a person or a collector alike. The offer it is
            for is either
            named (offer_id) or described: its store, MPN, condition and, for a one-off store, seller.

            on_unmatched says what to do with a described offer that cannot be matched to a drive (its
            MPN or condition is unknown, its drive's capacity is unknown, or its capacity disagrees
            with
            the drive's): reject refuses the price; queue keeps it for review, which needs the page
            and
            title a reviewer is shown.

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
