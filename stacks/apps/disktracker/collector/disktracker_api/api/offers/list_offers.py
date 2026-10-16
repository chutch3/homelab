from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.offer_summary import OfferSummary
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    *,
    store: None | str | Unset = UNSET,
    drive_id: None | Unset | UUID = UNSET,
    needs_recheck: bool | Unset = False,
    recent_days: int | Unset = 7,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_store: None | str | Unset
    if isinstance(store, Unset):
        json_store = UNSET
    else:
        json_store = store
    params["store"] = json_store

    json_drive_id: None | str | Unset
    if isinstance(drive_id, Unset):
        json_drive_id = UNSET
    elif isinstance(drive_id, UUID):
        json_drive_id = str(drive_id)
    else:
        json_drive_id = drive_id
    params["drive_id"] = json_drive_id

    params["needs_recheck"] = needs_recheck

    params["recent_days"] = recent_days


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/offers",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[OfferSummary] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = OfferSummary.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[OfferSummary]]:
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
    drive_id: None | Unset | UUID = UNSET,
    needs_recheck: bool | Unset = False,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | list[OfferSummary]]:
    """ List offers with their latest prices

     Return latest-price summaries, optionally narrowed by store or drive, ordered by title.
    With needs_recheck, return all manually priced offers not checked within recent_days,
    oldest checks first; store and drive filters are not applied in this mode. This list is
    not paginated.

    Args:
        store (None | str | Unset):
        drive_id (None | Unset | UUID):
        needs_recheck (bool | Unset):  Default: False.
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[OfferSummary]]
     """


    kwargs = _get_kwargs(
        store=store,
drive_id=drive_id,
needs_recheck=needs_recheck,
recent_days=recent_days,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,
    drive_id: None | Unset | UUID = UNSET,
    needs_recheck: bool | Unset = False,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | list[OfferSummary] | None:
    """ List offers with their latest prices

     Return latest-price summaries, optionally narrowed by store or drive, ordered by title.
    With needs_recheck, return all manually priced offers not checked within recent_days,
    oldest checks first; store and drive filters are not applied in this mode. This list is
    not paginated.

    Args:
        store (None | str | Unset):
        drive_id (None | Unset | UUID):
        needs_recheck (bool | Unset):  Default: False.
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[OfferSummary]
     """


    return sync_detailed(
        client=client,
store=store,
drive_id=drive_id,
needs_recheck=needs_recheck,
recent_days=recent_days,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,
    drive_id: None | Unset | UUID = UNSET,
    needs_recheck: bool | Unset = False,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | list[OfferSummary]]:
    """ List offers with their latest prices

     Return latest-price summaries, optionally narrowed by store or drive, ordered by title.
    With needs_recheck, return all manually priced offers not checked within recent_days,
    oldest checks first; store and drive filters are not applied in this mode. This list is
    not paginated.

    Args:
        store (None | str | Unset):
        drive_id (None | Unset | UUID):
        needs_recheck (bool | Unset):  Default: False.
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[OfferSummary]]
     """


    kwargs = _get_kwargs(
        store=store,
drive_id=drive_id,
needs_recheck=needs_recheck,
recent_days=recent_days,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    store: None | str | Unset = UNSET,
    drive_id: None | Unset | UUID = UNSET,
    needs_recheck: bool | Unset = False,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | list[OfferSummary] | None:
    """ List offers with their latest prices

     Return latest-price summaries, optionally narrowed by store or drive, ordered by title.
    With needs_recheck, return all manually priced offers not checked within recent_days,
    oldest checks first; store and drive filters are not applied in this mode. This list is
    not paginated.

    Args:
        store (None | str | Unset):
        drive_id (None | Unset | UUID):
        needs_recheck (bool | Unset):  Default: False.
        recent_days (int | Unset):  Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[OfferSummary]
     """


    return (await asyncio_detailed(
        client=client,
store=store,
drive_id=drive_id,
needs_recheck=needs_recheck,
recent_days=recent_days,

    )).parsed
