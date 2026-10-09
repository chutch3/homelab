from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.source_preview import SourcePreview
from ...models.source_preview_input import SourcePreviewInput
from typing import cast



def _get_kwargs(
    *,
    body: SourcePreviewInput,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/source-previews",
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | SourcePreview | None:
    if response.status_code == 200:
        response_200 = SourcePreview.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | SourcePreview]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: SourcePreviewInput,

) -> Response[HTTPValidationError | SourcePreview]:
    """ Preview Source

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (SourcePreviewInput): A source to try, saved or not. page_url: one of its pages to
            read instead of those its
            sitemap lists, so its settings can be tried on a page known to offer a drive.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SourcePreview]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    body: SourcePreviewInput,

) -> HTTPValidationError | SourcePreview | None:
    """ Preview Source

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (SourcePreviewInput): A source to try, saved or not. page_url: one of its pages to
            read instead of those its
            sitemap lists, so its settings can be tried on a page known to offer a drive.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SourcePreview
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: SourcePreviewInput,

) -> Response[HTTPValidationError | SourcePreview]:
    """ Preview Source

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (SourcePreviewInput): A source to try, saved or not. page_url: one of its pages to
            read instead of those its
            sitemap lists, so its settings can be tried on a page known to offer a drive.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | SourcePreview]
     """


    kwargs = _get_kwargs(
        body=body,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    body: SourcePreviewInput,

) -> HTTPValidationError | SourcePreview | None:
    """ Preview Source

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (SourcePreviewInput): A source to try, saved or not. page_url: one of its pages to
            read instead of those its
            sitemap lists, so its settings can be tried on a page known to offer a drive.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | SourcePreview
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
