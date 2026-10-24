from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.manual_source_view import ManualSourceView
from ...models.sap_commerce_source_view import SapCommerceSourceView
from ...models.shopify_source_view import ShopifySourceView
from ...models.sitemap_source_view import SitemapSourceView
from ...types import UNSET, Unset
from typing import cast



def _get_kwargs(
    *,
    due: bool | Unset = False,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["due"] = due


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/sources",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            def _parse_response_200_item(data: object) -> ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView:
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_0 = ManualSourceView.from_dict(data)



                    return response_200_item_type_0
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_1 = ShopifySourceView.from_dict(data)



                    return response_200_item_type_1
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                try:
                    if not isinstance(data, dict):
                        raise TypeError()
                    response_200_item_type_2 = SitemapSourceView.from_dict(data)



                    return response_200_item_type_2
                except (TypeError, ValueError, AttributeError, KeyError):
                    pass
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_item_type_3 = SapCommerceSourceView.from_dict(data)



                return response_200_item_type_3

            response_200_item = _parse_response_200_item(response_200_item_data)

            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient | Client,
    due: bool | Unset = False,

) -> Response[HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]]:
    """ List configured or due sources

     Every source by name; with due, only those due to run now, in the order to run them.
    Reading changes nothing.

    Args:
        due (bool | Unset): Only sources due now, ordered for collection; reading does not start a
            run. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]]
     """


    kwargs = _get_kwargs(
        due=due,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    due: bool | Unset = False,

) -> HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView] | None:
    """ List configured or due sources

     Every source by name; with due, only those due to run now, in the order to run them.
    Reading changes nothing.

    Args:
        due (bool | Unset): Only sources due now, ordered for collection; reading does not start a
            run. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]
     """


    return sync_detailed(
        client=client,
due=due,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    due: bool | Unset = False,

) -> Response[HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]]:
    """ List configured or due sources

     Every source by name; with due, only those due to run now, in the order to run them.
    Reading changes nothing.

    Args:
        due (bool | Unset): Only sources due now, ordered for collection; reading does not start a
            run. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]]
     """


    kwargs = _get_kwargs(
        due=due,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    due: bool | Unset = False,

) -> HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView] | None:
    """ List configured or due sources

     Every source by name; with due, only those due to run now, in the order to run them.
    Reading changes nothing.

    Args:
        due (bool | Unset): Only sources due now, ordered for collection; reading does not start a
            run. Default: False.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[ManualSourceView | SapCommerceSourceView | ShopifySourceView | SitemapSourceView]
     """


    return (await asyncio_detailed(
        client=client,
due=due,

    )).parsed
