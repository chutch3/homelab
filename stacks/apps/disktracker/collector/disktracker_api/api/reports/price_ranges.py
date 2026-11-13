from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.price_ranges_range_days import check_price_ranges_range_days
from ...models.price_ranges_range_days import PriceRangesRangeDays
from ...models.price_ranges_response_price_ranges import PriceRangesResponsePriceRanges
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    *,
    recent_days: int | Unset = 7,
    range_days: PriceRangesRangeDays | Unset = 90,
    drive_id: UUID,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["recent_days"] = recent_days

    json_range_days: int | Unset = UNSET
    if not isinstance(range_days, Unset):
        json_range_days = range_days

    params["range_days"] = json_range_days

    json_drive_id = str(drive_id)
    params["drive_id"] = json_drive_id


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/reports/price-ranges",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | PriceRangesResponsePriceRanges | None:
    if response.status_code == 200:
        response_200 = PriceRangesResponsePriceRanges.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | PriceRangesResponsePriceRanges]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: PriceRangesRangeDays | Unset = 90,
    drive_id: UUID,

) -> Response[HTTPValidationError | PriceRangesResponsePriceRanges]:
    """ Read a drive's price range in each condition

     Where a drive's lowest item price in each condition it is offered in has been over
    range_days (30, 90 or 180), from the offers that count (none held for review): null in a
    condition no offer of it was in stock in then. An offer unchecked for longer than
    recent_days is taken to have ended at its last check. A drive with no such offer, or none at
    all, has no range in any condition.

    Args:
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (PriceRangesRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PriceRangesResponsePriceRanges]
     """


    kwargs = _get_kwargs(
        recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: PriceRangesRangeDays | Unset = 90,
    drive_id: UUID,

) -> HTTPValidationError | PriceRangesResponsePriceRanges | None:
    """ Read a drive's price range in each condition

     Where a drive's lowest item price in each condition it is offered in has been over
    range_days (30, 90 or 180), from the offers that count (none held for review): null in a
    condition no offer of it was in stock in then. An offer unchecked for longer than
    recent_days is taken to have ended at its last check. A drive with no such offer, or none at
    all, has no range in any condition.

    Args:
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (PriceRangesRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PriceRangesResponsePriceRanges
     """


    return sync_detailed(
        client=client,
recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: PriceRangesRangeDays | Unset = 90,
    drive_id: UUID,

) -> Response[HTTPValidationError | PriceRangesResponsePriceRanges]:
    """ Read a drive's price range in each condition

     Where a drive's lowest item price in each condition it is offered in has been over
    range_days (30, 90 or 180), from the offers that count (none held for review): null in a
    condition no offer of it was in stock in then. An offer unchecked for longer than
    recent_days is taken to have ended at its last check. A drive with no such offer, or none at
    all, has no range in any condition.

    Args:
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (PriceRangesRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PriceRangesResponsePriceRanges]
     """


    kwargs = _get_kwargs(
        recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: PriceRangesRangeDays | Unset = 90,
    drive_id: UUID,

) -> HTTPValidationError | PriceRangesResponsePriceRanges | None:
    """ Read a drive's price range in each condition

     Where a drive's lowest item price in each condition it is offered in has been over
    range_days (30, 90 or 180), from the offers that count (none held for review): null in a
    condition no offer of it was in stock in then. An offer unchecked for longer than
    recent_days is taken to have ended at its last check. A drive with no such offer, or none at
    all, has no range in any condition.

    Args:
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (PriceRangesRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.
        drive_id (UUID):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PriceRangesResponsePriceRanges
     """


    return (await asyncio_detailed(
        client=client,
recent_days=recent_days,
range_days=range_days,
drive_id=drive_id,

    )).parsed
