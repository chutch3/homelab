from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.offer import Offer
from typing import cast
from uuid import UUID



def _get_kwargs(
    offer_id: UUID,

) -> dict[str, Any]:






    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/offers/{offer_id}".format(offer_id=quote(str(offer_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | Offer | None:
    if response.status_code == 200:
        response_200 = Offer.from_dict(response.json())



        return response_200

    if response.status_code == 404:
        response_404 = ErrorResponse.from_dict(response.json())



        return response_404

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | Offer]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[ErrorResponse | HTTPValidationError | Offer]:
    """ Get an offer and its price history

     Return an offer and its full price history, oldest first. Use GET /api/prices for a
    paginated history window.

    Args:
        offer_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Offer]
     """


    kwargs = _get_kwargs(
        offer_id=offer_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> ErrorResponse | HTTPValidationError | Offer | None:
    """ Get an offer and its price history

     Return an offer and its full price history, oldest first. Use GET /api/prices for a
    paginated history window.

    Args:
        offer_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Offer
     """


    return sync_detailed(
        offer_id=offer_id,
client=client,

    ).parsed

async def asyncio_detailed(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[ErrorResponse | HTTPValidationError | Offer]:
    """ Get an offer and its price history

     Return an offer and its full price history, oldest first. Use GET /api/prices for a
    paginated history window.

    Args:
        offer_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | Offer]
     """


    kwargs = _get_kwargs(
        offer_id=offer_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    offer_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> ErrorResponse | HTTPValidationError | Offer | None:
    """ Get an offer and its price history

     Return an offer and its full price history, oldest first. Use GET /api/prices for a
    paginated history window.

    Args:
        offer_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | Offer
     """


    return (await asyncio_detailed(
        offer_id=offer_id,
client=client,

    )).parsed
