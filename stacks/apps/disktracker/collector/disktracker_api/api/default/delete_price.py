from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.listing import Listing
from typing import cast
from uuid import UUID



def _get_kwargs(
    listing_id: UUID,
    observation_id: UUID,

) -> dict[str, Any]:






    _kwargs: dict[str, Any] = {
        "method": "delete",
        "url": "/api/listings/{listing_id}/observations/{observation_id}".format(listing_id=quote(str(listing_id), safe=""),observation_id=quote(str(observation_id), safe=""),),
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Any | HTTPValidationError | Listing | None:
    if response.status_code == 200:
        response_200 = Listing.from_dict(response.json())



        return response_200

    if response.status_code == 204:
        response_204 = cast(Any, None)
        return response_204

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[Any | HTTPValidationError | Listing]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    listing_id: UUID,
    observation_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Any | HTTPValidationError | Listing]:
    """ Delete Price

    Args:
        listing_id (UUID):
        observation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | Listing]
     """


    kwargs = _get_kwargs(
        listing_id=listing_id,
observation_id=observation_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    listing_id: UUID,
    observation_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Any | HTTPValidationError | Listing | None:
    """ Delete Price

    Args:
        listing_id (UUID):
        observation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | Listing
     """


    return sync_detailed(
        listing_id=listing_id,
observation_id=observation_id,
client=client,

    ).parsed

async def asyncio_detailed(
    listing_id: UUID,
    observation_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Response[Any | HTTPValidationError | Listing]:
    """ Delete Price

    Args:
        listing_id (UUID):
        observation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | HTTPValidationError | Listing]
     """


    kwargs = _get_kwargs(
        listing_id=listing_id,
observation_id=observation_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    listing_id: UUID,
    observation_id: UUID,
    *,
    client: AuthenticatedClient | Client,

) -> Any | HTTPValidationError | Listing | None:
    """ Delete Price

    Args:
        listing_id (UUID):
        observation_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | HTTPValidationError | Listing
     """


    return (await asyncio_detailed(
        listing_id=listing_id,
observation_id=observation_id,
client=client,

    )).parsed
