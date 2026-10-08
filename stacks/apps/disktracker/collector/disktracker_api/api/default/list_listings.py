from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.listing_summary import ListingSummary
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    store: None | str | Unset = UNSET,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_store: None | str | Unset
    if isinstance(store, Unset):
        json_store = UNSET
    else:
        json_store = store
    params["store"] = json_store


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/listings",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[ListingSummary] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = ListingSummary.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[ListingSummary]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,

) -> Response[HTTPValidationError | list[ListingSummary]]:
    """ List Listings

    Args:
        store (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ListingSummary]]
     """


    kwargs = _get_kwargs(
        store=store,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,

) -> HTTPValidationError | list[ListingSummary] | None:
    """ List Listings

    Args:
        store (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ListingSummary]
     """


    return sync_detailed(
        client=client,
store=store,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,

) -> Response[HTTPValidationError | list[ListingSummary]]:
    """ List Listings

    Args:
        store (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ListingSummary]]
     """


    kwargs = _get_kwargs(
        store=store,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,

) -> HTTPValidationError | list[ListingSummary] | None:
    """ List Listings

    Args:
        store (None | str | Unset):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ListingSummary]
     """


    return (await asyncio_detailed(
        client=client,
store=store,

    )).parsed
