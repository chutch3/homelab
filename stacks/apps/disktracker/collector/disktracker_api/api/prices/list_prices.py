from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.price_page import PricePage
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID
import datetime



def _get_kwargs(
    *,
    drive_id: None | Unset | UUID = UNSET,
    offer_id: None | Unset | UUID = UNSET,
    since: datetime.datetime | None | Unset = UNSET,
    until: datetime.datetime | None | Unset = UNSET,
    limit: int | Unset = 500,
    offset: int | Unset = 0,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_drive_id: None | str | Unset
    if isinstance(drive_id, Unset):
        json_drive_id = UNSET
    elif isinstance(drive_id, UUID):
        json_drive_id = str(drive_id)
    else:
        json_drive_id = drive_id
    params["drive_id"] = json_drive_id

    json_offer_id: None | str | Unset
    if isinstance(offer_id, Unset):
        json_offer_id = UNSET
    elif isinstance(offer_id, UUID):
        json_offer_id = str(offer_id)
    else:
        json_offer_id = offer_id
    params["offer_id"] = json_offer_id

    json_since: None | str | Unset
    if isinstance(since, Unset):
        json_since = UNSET
    elif isinstance(since, datetime.datetime):
        json_since = since.isoformat()
    else:
        json_since = since
    params["since"] = json_since

    json_until: None | str | Unset
    if isinstance(until, Unset):
        json_until = UNSET
    elif isinstance(until, datetime.datetime):
        json_until = until.isoformat()
    else:
        json_until = until
    params["until"] = json_until

    params["limit"] = limit

    params["offset"] = offset


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/prices",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | PricePage | None:
    if response.status_code == 200:
        response_200 = PricePage.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | PricePage]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    drive_id: None | Unset | UUID = UNSET,
    offer_id: None | Unset | UUID = UNSET,
    since: datetime.datetime | None | Unset = UNSET,
    until: datetime.datetime | None | Unset = UNSET,
    limit: int | Unset = 500,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | PricePage]:
    """ Read price history

     Supply exactly one of drive_id or offer_id. Return observations oldest first, ordered by
    observed_at, entered_at and id, using limit/offset pagination. since and until are inclusive;
    the result also includes each offer's last observation before since to establish the price
    in effect when the window opens. total counts matching observations, including those opening
    values, before pagination. An unknown drive or offer returns an empty page.

    Args:
        drive_id (None | Unset | UUID): Drive UUID. Supply exactly one of drive_id or offer_id.
        offer_id (None | Unset | UUID): Offer UUID. Supply exactly one of drive_id or offer_id.
        since (datetime.datetime | None | Unset): Inclusive window start. Includes the last price
            before this time for each offer to establish the opening value.
        until (datetime.datetime | None | Unset): Inclusive window end; omit for no upper time
            bound.
        limit (int | Unset): Maximum observations in this page, including opening values. Default:
            500.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PricePage]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,
offer_id=offer_id,
since=since,
until=until,
limit=limit,
offset=offset,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    drive_id: None | Unset | UUID = UNSET,
    offer_id: None | Unset | UUID = UNSET,
    since: datetime.datetime | None | Unset = UNSET,
    until: datetime.datetime | None | Unset = UNSET,
    limit: int | Unset = 500,
    offset: int | Unset = 0,

) -> HTTPValidationError | PricePage | None:
    """ Read price history

     Supply exactly one of drive_id or offer_id. Return observations oldest first, ordered by
    observed_at, entered_at and id, using limit/offset pagination. since and until are inclusive;
    the result also includes each offer's last observation before since to establish the price
    in effect when the window opens. total counts matching observations, including those opening
    values, before pagination. An unknown drive or offer returns an empty page.

    Args:
        drive_id (None | Unset | UUID): Drive UUID. Supply exactly one of drive_id or offer_id.
        offer_id (None | Unset | UUID): Offer UUID. Supply exactly one of drive_id or offer_id.
        since (datetime.datetime | None | Unset): Inclusive window start. Includes the last price
            before this time for each offer to establish the opening value.
        until (datetime.datetime | None | Unset): Inclusive window end; omit for no upper time
            bound.
        limit (int | Unset): Maximum observations in this page, including opening values. Default:
            500.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PricePage
     """


    return sync_detailed(
        client=client,
drive_id=drive_id,
offer_id=offer_id,
since=since,
until=until,
limit=limit,
offset=offset,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    drive_id: None | Unset | UUID = UNSET,
    offer_id: None | Unset | UUID = UNSET,
    since: datetime.datetime | None | Unset = UNSET,
    until: datetime.datetime | None | Unset = UNSET,
    limit: int | Unset = 500,
    offset: int | Unset = 0,

) -> Response[HTTPValidationError | PricePage]:
    """ Read price history

     Supply exactly one of drive_id or offer_id. Return observations oldest first, ordered by
    observed_at, entered_at and id, using limit/offset pagination. since and until are inclusive;
    the result also includes each offer's last observation before since to establish the price
    in effect when the window opens. total counts matching observations, including those opening
    values, before pagination. An unknown drive or offer returns an empty page.

    Args:
        drive_id (None | Unset | UUID): Drive UUID. Supply exactly one of drive_id or offer_id.
        offer_id (None | Unset | UUID): Offer UUID. Supply exactly one of drive_id or offer_id.
        since (datetime.datetime | None | Unset): Inclusive window start. Includes the last price
            before this time for each offer to establish the opening value.
        until (datetime.datetime | None | Unset): Inclusive window end; omit for no upper time
            bound.
        limit (int | Unset): Maximum observations in this page, including opening values. Default:
            500.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | PricePage]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,
offer_id=offer_id,
since=since,
until=until,
limit=limit,
offset=offset,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    drive_id: None | Unset | UUID = UNSET,
    offer_id: None | Unset | UUID = UNSET,
    since: datetime.datetime | None | Unset = UNSET,
    until: datetime.datetime | None | Unset = UNSET,
    limit: int | Unset = 500,
    offset: int | Unset = 0,

) -> HTTPValidationError | PricePage | None:
    """ Read price history

     Supply exactly one of drive_id or offer_id. Return observations oldest first, ordered by
    observed_at, entered_at and id, using limit/offset pagination. since and until are inclusive;
    the result also includes each offer's last observation before since to establish the price
    in effect when the window opens. total counts matching observations, including those opening
    values, before pagination. An unknown drive or offer returns an empty page.

    Args:
        drive_id (None | Unset | UUID): Drive UUID. Supply exactly one of drive_id or offer_id.
        offer_id (None | Unset | UUID): Offer UUID. Supply exactly one of drive_id or offer_id.
        since (datetime.datetime | None | Unset): Inclusive window start. Includes the last price
            before this time for each offer to establish the opening value.
        until (datetime.datetime | None | Unset): Inclusive window end; omit for no upper time
            bound.
        limit (int | Unset): Maximum observations in this page, including opening values. Default:
            500.
        offset (int | Unset): Number of matching items to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | PricePage
     """


    return (await asyncio_detailed(
        client=client,
drive_id=drive_id,
offer_id=offer_id,
since=since,
until=until,
limit=limit,
offset=offset,

    )).parsed
