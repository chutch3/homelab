from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.drive_detail import DriveDetail
from ...models.error_response import ErrorResponse
from ...models.get_drive_range_days import check_get_drive_range_days
from ...models.get_drive_range_days import GetDriveRangeDays
from ...models.http_validation_error import HTTPValidationError
from ...types import UNSET, Unset
from typing import cast
from uuid import UUID



def _get_kwargs(
    drive_id: UUID,
    *,
    recent_days: int | Unset = 7,
    range_days: GetDriveRangeDays | Unset = 90,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["recent_days"] = recent_days

    json_range_days: int | Unset = UNSET
    if not isinstance(range_days, Unset):
        json_range_days = range_days

    params["range_days"] = json_range_days


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/drives/{drive_id}".format(drive_id=quote(str(drive_id), safe=""),),
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> DriveDetail | ErrorResponse | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = DriveDetail.from_dict(response.json())



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


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[DriveDetail | ErrorResponse | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: GetDriveRangeDays | Unset = 90,

) -> Response[DriveDetail | ErrorResponse | HTTPValidationError]:
    """ Get a drive and its offers

     A drive with every offer of it, and the range of its price in each condition.

    Args:
        drive_id (UUID):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (GetDriveRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DriveDetail | ErrorResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,
recent_days=recent_days,
range_days=range_days,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: GetDriveRangeDays | Unset = 90,

) -> DriveDetail | ErrorResponse | HTTPValidationError | None:
    """ Get a drive and its offers

     A drive with every offer of it, and the range of its price in each condition.

    Args:
        drive_id (UUID):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (GetDriveRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DriveDetail | ErrorResponse | HTTPValidationError
     """


    return sync_detailed(
        drive_id=drive_id,
client=client,
recent_days=recent_days,
range_days=range_days,

    ).parsed

async def asyncio_detailed(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: GetDriveRangeDays | Unset = 90,

) -> Response[DriveDetail | ErrorResponse | HTTPValidationError]:
    """ Get a drive and its offers

     A drive with every offer of it, and the range of its price in each condition.

    Args:
        drive_id (UUID):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (GetDriveRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[DriveDetail | ErrorResponse | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        drive_id=drive_id,
recent_days=recent_days,
range_days=range_days,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    drive_id: UUID,
    *,
    client: AuthenticatedClient | Client,
    recent_days: int | Unset = 7,
    range_days: GetDriveRangeDays | Unset = 90,

) -> DriveDetail | ErrorResponse | HTTPValidationError | None:
    """ Get a drive and its offers

     A drive with every offer of it, and the range of its price in each condition.

    Args:
        drive_id (UUID):
        recent_days (int | Unset): What checked recently means Default: 7.
        range_days (GetDriveRangeDays | Unset): How far back each price range looks, in days.
            Default: 90.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        DriveDetail | ErrorResponse | HTTPValidationError
     """


    return (await asyncio_detailed(
        drive_id=drive_id,
client=client,
recent_days=recent_days,
range_days=range_days,

    )).parsed
