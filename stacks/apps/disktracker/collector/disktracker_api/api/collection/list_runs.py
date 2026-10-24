from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.list_runs_status_type_0 import check_list_runs_status_type_0
from ...models.list_runs_status_type_0 import ListRunsStatusType0
from ...models.run import Run
from ...types import UNSET, Unset
from typing import cast
import datetime



def _get_kwargs(
    *,
    source: None | str | Unset = UNSET,
    status: ListRunsStatusType0 | None | Unset = UNSET,
    finished_since: datetime.datetime | None | Unset = UNSET,
    latest_per_source: bool | Unset = False,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    json_source: None | str | Unset
    if isinstance(source, Unset):
        json_source = UNSET
    else:
        json_source = source
    params["source"] = json_source

    json_status: None | str | Unset
    if isinstance(status, Unset):
        json_status = UNSET
    elif isinstance(status, str):
        json_status = status
    else:
        json_status = status
    params["status"] = json_status

    json_finished_since: None | str | Unset
    if isinstance(finished_since, Unset):
        json_finished_since = UNSET
    elif isinstance(finished_since, datetime.datetime):
        json_finished_since = finished_since.isoformat()
    else:
        json_finished_since = finished_since
    params["finished_since"] = json_finished_since

    params["latest_per_source"] = latest_per_source


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/collection-runs",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[Run] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = Run.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[Run]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    status: ListRunsStatusType0 | None | Unset = UNSET,
    finished_since: datetime.datetime | None | Unset = UNSET,
    latest_per_source: bool | Unset = False,

) -> Response[HTTPValidationError | list[Run]]:
    """ List collection runs

     Return runs oldest first, filtered by source key, status and finished_since. With
    latest_per_source=true, return the latest matching run of each source, ordered by source
    key. This list is not paginated.

    Args:
        source (None | str | Unset): Filter by source key, not source UUID.
        status (ListRunsStatusType0 | None | Unset):
        finished_since (datetime.datetime | None | Unset): Only runs finished at or after this
            timezone-aware timestamp.
        latest_per_source (bool | Unset): Return only the latest matching run per source, ordered
            by source key. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[Run]]
     """


    kwargs = _get_kwargs(
        source=source,
status=status,
finished_since=finished_since,
latest_per_source=latest_per_source,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    status: ListRunsStatusType0 | None | Unset = UNSET,
    finished_since: datetime.datetime | None | Unset = UNSET,
    latest_per_source: bool | Unset = False,

) -> HTTPValidationError | list[Run] | None:
    """ List collection runs

     Return runs oldest first, filtered by source key, status and finished_since. With
    latest_per_source=true, return the latest matching run of each source, ordered by source
    key. This list is not paginated.

    Args:
        source (None | str | Unset): Filter by source key, not source UUID.
        status (ListRunsStatusType0 | None | Unset):
        finished_since (datetime.datetime | None | Unset): Only runs finished at or after this
            timezone-aware timestamp.
        latest_per_source (bool | Unset): Return only the latest matching run per source, ordered
            by source key. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[Run]
     """


    return sync_detailed(
        client=client,
source=source,
status=status,
finished_since=finished_since,
latest_per_source=latest_per_source,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    status: ListRunsStatusType0 | None | Unset = UNSET,
    finished_since: datetime.datetime | None | Unset = UNSET,
    latest_per_source: bool | Unset = False,

) -> Response[HTTPValidationError | list[Run]]:
    """ List collection runs

     Return runs oldest first, filtered by source key, status and finished_since. With
    latest_per_source=true, return the latest matching run of each source, ordered by source
    key. This list is not paginated.

    Args:
        source (None | str | Unset): Filter by source key, not source UUID.
        status (ListRunsStatusType0 | None | Unset):
        finished_since (datetime.datetime | None | Unset): Only runs finished at or after this
            timezone-aware timestamp.
        latest_per_source (bool | Unset): Return only the latest matching run per source, ordered
            by source key. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[Run]]
     """


    kwargs = _get_kwargs(
        source=source,
status=status,
finished_since=finished_since,
latest_per_source=latest_per_source,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    source: None | str | Unset = UNSET,
    status: ListRunsStatusType0 | None | Unset = UNSET,
    finished_since: datetime.datetime | None | Unset = UNSET,
    latest_per_source: bool | Unset = False,

) -> HTTPValidationError | list[Run] | None:
    """ List collection runs

     Return runs oldest first, filtered by source key, status and finished_since. With
    latest_per_source=true, return the latest matching run of each source, ordered by source
    key. This list is not paginated.

    Args:
        source (None | str | Unset): Filter by source key, not source UUID.
        status (ListRunsStatusType0 | None | Unset):
        finished_since (datetime.datetime | None | Unset): Only runs finished at or after this
            timezone-aware timestamp.
        latest_per_source (bool | Unset): Return only the latest matching run per source, ordered
            by source key. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[Run]
     """


    return (await asyncio_detailed(
        client=client,
source=source,
status=status,
finished_since=finished_since,
latest_per_source=latest_per_source,

    )).parsed
