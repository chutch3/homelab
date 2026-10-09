from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.scraped_input import ScrapedInput
from ...models.scraped_result import ScrapedResult
from typing import cast
from uuid import UUID



def _get_kwargs(
    *,
    body: ScrapedInput,
    idempotency_key: UUID,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}
    headers["idempotency-key"] = idempotency_key







    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/scraped",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | ScrapedResult | None:
    if response.status_code == 200:
        response_200 = ScrapedResult.from_dict(response.json())



        return response_200

    if response.status_code == 201:
        response_201 = ScrapedResult.from_dict(response.json())



        return response_201

    if response.status_code == 202:
        response_202 = ScrapedResult.from_dict(response.json())



        return response_202

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | ScrapedResult]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ScrapedInput,
    idempotency_key: UUID,

) -> Response[HTTPValidationError | ScrapedResult]:
    """ Record Scraped

    Args:
        idempotency_key (UUID):
        body (ScrapedInput): An offer as a collector saw it at its source, which is the store it
            is recorded under;
            MPN or condition may be missing until reviewed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ScrapedResult]
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
    body: ScrapedInput,
    idempotency_key: UUID,

) -> HTTPValidationError | ScrapedResult | None:
    """ Record Scraped

    Args:
        idempotency_key (UUID):
        body (ScrapedInput): An offer as a collector saw it at its source, which is the store it
            is recorded under;
            MPN or condition may be missing until reviewed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ScrapedResult
     """


    return sync_detailed(
        client=client,
body=body,
idempotency_key=idempotency_key,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ScrapedInput,
    idempotency_key: UUID,

) -> Response[HTTPValidationError | ScrapedResult]:
    """ Record Scraped

    Args:
        idempotency_key (UUID):
        body (ScrapedInput): An offer as a collector saw it at its source, which is the store it
            is recorded under;
            MPN or condition may be missing until reviewed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | ScrapedResult]
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
    body: ScrapedInput,
    idempotency_key: UUID,

) -> HTTPValidationError | ScrapedResult | None:
    """ Record Scraped

    Args:
        idempotency_key (UUID):
        body (ScrapedInput): An offer as a collector saw it at its source, which is the store it
            is recorded under;
            MPN or condition may be missing until reviewed.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | ScrapedResult
     """


    return (await asyncio_detailed(
        client=client,
body=body,
idempotency_key=idempotency_key,

    )).parsed
