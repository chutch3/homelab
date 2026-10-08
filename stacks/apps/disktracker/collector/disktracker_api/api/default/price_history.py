from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.listing import Listing
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    *,
    listing: list[UUID] | None | Unset = UNSET,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_listing: list[str] | None | Unset
    if isinstance(listing, Unset):
        json_listing = UNSET
    elif isinstance(listing, list):
        json_listing = []
        for listing_type_0_item_data in listing:
            listing_type_0_item = str(listing_type_0_item_data)
            json_listing.append(listing_type_0_item)


    else:
        json_listing = listing
    params["listing"] = json_listing


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/price-history",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[Listing] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = Listing.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[Listing]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    listing: list[UUID] | None | Unset = UNSET,

) -> Response[HTTPValidationError | list[Listing]]:
    """ Price History

    Args:
        listing (list[UUID] | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[Listing]]
     """


    kwargs = _get_kwargs(
        listing=listing,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    listing: list[UUID] | None | Unset = UNSET,

) -> HTTPValidationError | list[Listing] | None:
    """ Price History

    Args:
        listing (list[UUID] | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[Listing]
     """


    return sync_detailed(
        client=client,
listing=listing,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    listing: list[UUID] | None | Unset = UNSET,

) -> Response[HTTPValidationError | list[Listing]]:
    """ Price History

    Args:
        listing (list[UUID] | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[Listing]]
     """


    kwargs = _get_kwargs(
        listing=listing,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    listing: list[UUID] | None | Unset = UNSET,

) -> HTTPValidationError | list[Listing] | None:
    """ Price History

    Args:
        listing (list[UUID] | None | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[Listing]
     """


    return (await asyncio_detailed(
        client=client,
listing=listing,

    )).parsed
