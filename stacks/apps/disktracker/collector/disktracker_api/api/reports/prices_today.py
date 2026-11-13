from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.price_mark import PriceMark
from ...models.prices_today_condition_item import check_prices_today_condition_item
from ...models.prices_today_condition_item import PricesTodayConditionItem
from ...models.prices_today_form_factor_type_0 import check_prices_today_form_factor_type_0
from ...models.prices_today_form_factor_type_0 import PricesTodayFormFactorType0
from ...models.prices_today_intended_use_type_0 import check_prices_today_intended_use_type_0
from ...models.prices_today_intended_use_type_0 import PricesTodayIntendedUseType0
from ...models.prices_today_interface_type_0 import check_prices_today_interface_type_0
from ...models.prices_today_interface_type_0 import PricesTodayInterfaceType0
from ...models.prices_today_media_type_type_0 import check_prices_today_media_type_type_0
from ...models.prices_today_media_type_type_0 import PricesTodayMediaTypeType0
from ...models.prices_today_recording_type_type_0 import check_prices_today_recording_type_type_0
from ...models.prices_today_recording_type_type_0 import PricesTodayRecordingTypeType0
from ...types import UNSET, Unset
from typing import cast
from typing import Literal, cast



def _get_kwargs(
    *,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[PricesTodayConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PricesTodayMediaTypeType0 | Unset = UNSET,
    form_factor: None | PricesTodayFormFactorType0 | Unset = UNSET,
    interface: None | PricesTodayInterfaceType0 | Unset = UNSET,
    recording_type: None | PricesTodayRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> dict[str, Any]:




    params: dict[str, Any] = {}

    params["q"] = q

    json_brand: list[str] | Unset = UNSET
    if not isinstance(brand, Unset):
        json_brand = brand


    params["brand"] = json_brand

    json_capacity: list[int] | Unset = UNSET
    if not isinstance(capacity, Unset):
        json_capacity = capacity


    params["capacity"] = json_capacity

    json_condition: list[str] | Unset = UNSET
    if not isinstance(condition, Unset):
        json_condition = []
        for condition_item_data in condition:
            condition_item: str = condition_item_data
            json_condition.append(condition_item)


    params["condition"] = json_condition

    json_store: list[str] | Unset = UNSET
    if not isinstance(store, Unset):
        json_store = store


    params["store"] = json_store

    json_media_type: None | str | Unset
    if isinstance(media_type, Unset):
        json_media_type = UNSET
    elif isinstance(media_type, str):
        json_media_type = media_type
    else:
        json_media_type = media_type
    params["media_type"] = json_media_type

    json_form_factor: None | str | Unset
    if isinstance(form_factor, Unset):
        json_form_factor = UNSET
    elif isinstance(form_factor, str):
        json_form_factor = form_factor
    else:
        json_form_factor = form_factor
    params["form_factor"] = json_form_factor

    json_interface: None | str | Unset
    if isinstance(interface, Unset):
        json_interface = UNSET
    elif isinstance(interface, str):
        json_interface = interface
    else:
        json_interface = interface
    params["interface"] = json_interface

    json_recording_type: None | str | Unset
    if isinstance(recording_type, Unset):
        json_recording_type = UNSET
    elif isinstance(recording_type, str):
        json_recording_type = recording_type
    else:
        json_recording_type = recording_type
    params["recording_type"] = json_recording_type

    json_intended_use: Literal['unknown'] | None | str | Unset
    if isinstance(intended_use, Unset):
        json_intended_use = UNSET
    elif isinstance(intended_use, str):
        json_intended_use = intended_use
    else:
        json_intended_use = intended_use
    params["intended_use"] = json_intended_use

    params["recent_days"] = recent_days


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/reports/prices-today",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | list[PriceMark] | None:
    if response.status_code == 200:
        response_200 = []
        _response_200 = response.json()
        for response_200_item_data in (_response_200):
            response_200_item = PriceMark.from_dict(response_200_item_data)



            response_200.append(response_200_item)

        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | list[PriceMark]]:
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
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[PricesTodayConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PricesTodayMediaTypeType0 | Unset = UNSET,
    form_factor: None | PricesTodayFormFactorType0 | Unset = UNSET,
    interface: None | PricesTodayInterfaceType0 | Unset = UNSET,
    recording_type: None | PricesTodayRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | list[PriceMark]]:
    """ Read current prices per terabyte

     What each drive asked for (every drive, or narrowed by the same filters as the drives
    list) costs today in each condition it is in stock in, by item price per terabyte, cheapest
    first. recent_days: the lowest is the cheapest of those checked within it.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PricesTodayConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PricesTodayMediaTypeType0 | Unset):
        form_factor (None | PricesTodayFormFactorType0 | Unset):
        interface (None | PricesTodayInterfaceType0 | Unset):
        recording_type (None | PricesTodayRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset):
        recent_days (int | Unset): Only offers checked within this many days can be marked lowest.
            Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[PriceMark]]
     """


    kwargs = _get_kwargs(
        q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,

    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)

def sync(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[PricesTodayConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PricesTodayMediaTypeType0 | Unset = UNSET,
    form_factor: None | PricesTodayFormFactorType0 | Unset = UNSET,
    interface: None | PricesTodayInterfaceType0 | Unset = UNSET,
    recording_type: None | PricesTodayRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | list[PriceMark] | None:
    """ Read current prices per terabyte

     What each drive asked for (every drive, or narrowed by the same filters as the drives
    list) costs today in each condition it is in stock in, by item price per terabyte, cheapest
    first. recent_days: the lowest is the cheapest of those checked within it.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PricesTodayConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PricesTodayMediaTypeType0 | Unset):
        form_factor (None | PricesTodayFormFactorType0 | Unset):
        interface (None | PricesTodayInterfaceType0 | Unset):
        recording_type (None | PricesTodayRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset):
        recent_days (int | Unset): Only offers checked within this many days can be marked lowest.
            Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[PriceMark]
     """


    return sync_detailed(
        client=client,
q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[PricesTodayConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PricesTodayMediaTypeType0 | Unset = UNSET,
    form_factor: None | PricesTodayFormFactorType0 | Unset = UNSET,
    interface: None | PricesTodayInterfaceType0 | Unset = UNSET,
    recording_type: None | PricesTodayRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | list[PriceMark]]:
    """ Read current prices per terabyte

     What each drive asked for (every drive, or narrowed by the same filters as the drives
    list) costs today in each condition it is in stock in, by item price per terabyte, cheapest
    first. recent_days: the lowest is the cheapest of those checked within it.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PricesTodayConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PricesTodayMediaTypeType0 | Unset):
        form_factor (None | PricesTodayFormFactorType0 | Unset):
        interface (None | PricesTodayInterfaceType0 | Unset):
        recording_type (None | PricesTodayRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset):
        recent_days (int | Unset): Only offers checked within this many days can be marked lowest.
            Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | list[PriceMark]]
     """


    kwargs = _get_kwargs(
        q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,

    )

    response = await client.get_async_httpx_client().request(
        **kwargs
    )

    return _build_response(client=client, response=response)

async def asyncio(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[PricesTodayConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PricesTodayMediaTypeType0 | Unset = UNSET,
    form_factor: None | PricesTodayFormFactorType0 | Unset = UNSET,
    interface: None | PricesTodayInterfaceType0 | Unset = UNSET,
    recording_type: None | PricesTodayRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | list[PriceMark] | None:
    """ Read current prices per terabyte

     What each drive asked for (every drive, or narrowed by the same filters as the drives
    list) costs today in each condition it is in stock in, by item price per terabyte, cheapest
    first. recent_days: the lowest is the cheapest of those checked within it.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PricesTodayConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PricesTodayMediaTypeType0 | Unset):
        form_factor (None | PricesTodayFormFactorType0 | Unset):
        interface (None | PricesTodayInterfaceType0 | Unset):
        recording_type (None | PricesTodayRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PricesTodayIntendedUseType0 | Unset):
        recent_days (int | Unset): Only offers checked within this many days can be marked lowest.
            Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | list[PriceMark]
     """


    return (await asyncio_detailed(
        client=client,
q=q,
brand=brand,
capacity=capacity,
condition=condition,
store=store,
media_type=media_type,
form_factor=form_factor,
interface=interface,
recording_type=recording_type,
intended_use=intended_use,
recent_days=recent_days,

    )).parsed
