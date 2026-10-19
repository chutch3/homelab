from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.catalog_drive_page import CatalogDrivePage
from ...models.http_validation_error import HTTPValidationError
from ...models.list_catalog_drives_issue_type_0 import check_list_catalog_drives_issue_type_0
from ...models.list_catalog_drives_issue_type_0 import ListCatalogDrivesIssueType0
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    q: str | Unset = '',
    issue: ListCatalogDrivesIssueType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["q"] = q

    json_issue: None | str | Unset
    if isinstance(issue, Unset):
        json_issue = UNSET
    elif isinstance(issue, str):
        json_issue = issue
    else:
        json_issue = issue
    params["issue"] = json_issue

    params["recent_days"] = recent_days

    params["limit"] = limit

    params["offset"] = offset


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/catalog-drives",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> CatalogDrivePage | HTTPValidationError | None:
    if response.status_code == 200:
        response_200 = CatalogDrivePage.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[CatalogDrivePage | HTTPValidationError]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    issue: ListCatalogDrivesIssueType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> Response[CatalogDrivePage | HTTPValidationError]:
    """ List every drive to manage

     Every drive, offers held for review and all, a page at a time: those named by q exactly
    (by MPN or another MPN) first, then in stock first and cheapest per terabyte first. Each has
    how many offers it has and what it needs; issues counts every drive needing each.

    Args:
        q (str | Unset):  Default: ''.
        issue (ListCatalogDrivesIssueType0 | None | Unset): Only drives that need this
        recent_days (int | Unset): What checked recently means Default: 7.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching drives to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogDrivePage | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        q=q,
issue=issue,
recent_days=recent_days,
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
    q: str | Unset = '',
    issue: ListCatalogDrivesIssueType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> CatalogDrivePage | HTTPValidationError | None:
    """ List every drive to manage

     Every drive, offers held for review and all, a page at a time: those named by q exactly
    (by MPN or another MPN) first, then in stock first and cheapest per terabyte first. Each has
    how many offers it has and what it needs; issues counts every drive needing each.

    Args:
        q (str | Unset):  Default: ''.
        issue (ListCatalogDrivesIssueType0 | None | Unset): Only drives that need this
        recent_days (int | Unset): What checked recently means Default: 7.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching drives to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogDrivePage | HTTPValidationError
     """


    return sync_detailed(
        client=client,
q=q,
issue=issue,
recent_days=recent_days,
limit=limit,
offset=offset,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    issue: ListCatalogDrivesIssueType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> Response[CatalogDrivePage | HTTPValidationError]:
    """ List every drive to manage

     Every drive, offers held for review and all, a page at a time: those named by q exactly
    (by MPN or another MPN) first, then in stock first and cheapest per terabyte first. Each has
    how many offers it has and what it needs; issues counts every drive needing each.

    Args:
        q (str | Unset):  Default: ''.
        issue (ListCatalogDrivesIssueType0 | None | Unset): Only drives that need this
        recent_days (int | Unset): What checked recently means Default: 7.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching drives to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[CatalogDrivePage | HTTPValidationError]
     """


    kwargs = _get_kwargs(
        q=q,
issue=issue,
recent_days=recent_days,
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
    q: str | Unset = '',
    issue: ListCatalogDrivesIssueType0 | None | Unset = UNSET,
    recent_days: int | Unset = 7,
    limit: int | Unset = 50,
    offset: int | Unset = 0,

) -> CatalogDrivePage | HTTPValidationError | None:
    """ List every drive to manage

     Every drive, offers held for review and all, a page at a time: those named by q exactly
    (by MPN or another MPN) first, then in stock first and cheapest per terabyte first. Each has
    how many offers it has and what it needs; issues counts every drive needing each.

    Args:
        q (str | Unset):  Default: ''.
        issue (ListCatalogDrivesIssueType0 | None | Unset): Only drives that need this
        recent_days (int | Unset): What checked recently means Default: 7.
        limit (int | Unset): Maximum drives in this page. Default: 50.
        offset (int | Unset): Number of matching drives to skip. Default: 0.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        CatalogDrivePage | HTTPValidationError
     """


    return (await asyncio_detailed(
        client=client,
q=q,
issue=issue,
recent_days=recent_days,
limit=limit,
offset=offset,

    )).parsed
