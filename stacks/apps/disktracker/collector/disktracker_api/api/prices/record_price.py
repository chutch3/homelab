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
    if response.status_code == 201:
        response_201 = PriceResult.from_dict(response.json())



        return response_201

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
    """ Record a price of a known drive's offer

     Record a price of an offer whose drive is already known. The Idempotency-Key names the
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
    unchanged price is recorded with price_id null, counted as a check.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price of an offer whose drive is already known, from a
            person or a collector
            rechecking it. The offer is named (offer_id), or its drive is (drive_id), with the store,
            seller and condition it is offered in: an offer new to them is made, titled and addressed
            by
            title and url when given. Nothing here says what a drive is: a drive is made or corrected
            beforehand, and a store page described is taken in at /ingestions.

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
    """ Record a price of a known drive's offer

     Record a price of an offer whose drive is already known. The Idempotency-Key names the
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
    unchanged price is recorded with price_id null, counted as a check.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price of an offer whose drive is already known, from a
            person or a collector
            rechecking it. The offer is named (offer_id), or its drive is (drive_id), with the store,
            seller and condition it is offered in: an offer new to them is made, titled and addressed
            by
            title and url when given. Nothing here says what a drive is: a drive is made or corrected
            beforehand, and a store page described is taken in at /ingestions.

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
    """ Record a price of a known drive's offer

     Record a price of an offer whose drive is already known. The Idempotency-Key names the
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
    unchanged price is recorded with price_id null, counted as a check.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price of an offer whose drive is already known, from a
            person or a collector
            rechecking it. The offer is named (offer_id), or its drive is (drive_id), with the store,
            seller and condition it is offered in: an offer new to them is made, titled and addressed
            by
            title and url when given. Nothing here says what a drive is: a drive is made or corrected
            beforehand, and a store page described is taken in at /ingestions.

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
    """ Record a price of a known drive's offer

     Record a price of an offer whose drive is already known. The Idempotency-Key names the
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
    unchanged price is recorded with price_id null, counted as a check.

    Args:
        idempotency_key (UUID): New UUID for each submission. Retry using the same key and body;
            changing the body returns 409.
        body (PriceInput): One observed price of an offer whose drive is already known, from a
            person or a collector
            rechecking it. The offer is named (offer_id), or its drive is (drive_id), with the store,
            seller and condition it is offered in: an offer new to them is made, titled and addressed
            by
            title and url when given. Nothing here says what a drive is: a drive is made or corrected
            beforehand, and a store page described is taken in at /ingestions.

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
