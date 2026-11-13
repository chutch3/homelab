from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.error_response import ErrorResponse
from ...models.http_validation_error import HTTPValidationError
from ...models.manual_source_preview_input import ManualSourcePreviewInput
from ...models.sap_commerce_source_preview_input import SapCommerceSourcePreviewInput
from ...models.shopify_source_preview_input import ShopifySourcePreviewInput
from ...models.sitemap_source_preview_input import SitemapSourcePreviewInput
from ...models.source_preview import SourcePreview
from typing import cast



def _get_kwargs(
    *,
    body: ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput | SitemapSourcePreviewInput,

) -> dict[str, Any]:
    headers: dict[str, Any] = {}






    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/api/source-previews",
    }


    if isinstance(body, ManualSourcePreviewInput):
        _kwargs["json"] = body.to_dict()
    elif isinstance(body, ShopifySourcePreviewInput):
        _kwargs["json"] = body.to_dict()
    elif isinstance(body, SitemapSourcePreviewInput):
        _kwargs["json"] = body.to_dict()
    else:
        _kwargs["json"] = body.to_dict()


    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> ErrorResponse | HTTPValidationError | SourcePreview | None:
    if response.status_code == 200:
        response_200 = SourcePreview.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if response.status_code == 503:
        response_503 = ErrorResponse.from_dict(response.json())



        return response_503

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[ErrorResponse | HTTPValidationError | SourcePreview]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput | SitemapSourcePreviewInput,

) -> Response[ErrorResponse | HTTPValidationError | SourcePreview]:
    """ Preview a source without saving it

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput
            | SitemapSourcePreviewInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | SourcePreview]
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
    body: ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput | SitemapSourcePreviewInput,

) -> ErrorResponse | HTTPValidationError | SourcePreview | None:
    """ Preview a source without saving it

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput
            | SitemapSourcePreviewInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | SourcePreview
     """


    return sync_detailed(
        client=client,
body=body,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    body: ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput | SitemapSourcePreviewInput,

) -> Response[ErrorResponse | HTTPValidationError | SourcePreview]:
    """ Preview a source without saving it

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput
            | SitemapSourcePreviewInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[ErrorResponse | HTTPValidationError | SourcePreview]
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
    body: ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput | SitemapSourcePreviewInput,

) -> ErrorResponse | HTTPValidationError | SourcePreview | None:
    """ Preview a source without saving it

     Try a source, saved or not: one offer as the collector reads it, and what recording
    it would do. Nothing is kept.

    Args:
        body (ManualSourcePreviewInput | SapCommerceSourcePreviewInput | ShopifySourcePreviewInput
            | SitemapSourcePreviewInput):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        ErrorResponse | HTTPValidationError | SourcePreview
     """


    return (await asyncio_detailed(
        client=client,
body=body,

    )).parsed
