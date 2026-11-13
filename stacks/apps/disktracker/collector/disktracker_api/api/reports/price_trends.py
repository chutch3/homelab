from http import HTTPStatus
from typing import Any, cast
from urllib.parse import quote

import httpx

from ...client import AuthenticatedClient, Client
from ...types import Response, UNSET
from ... import errors

from ...models.http_validation_error import HTTPValidationError
from ...models.price_trends_by_type_0 import check_price_trends_by_type_0
from ...models.price_trends_by_type_0 import PriceTrendsByType0
from ...models.price_trends_condition_item import check_price_trends_condition_item
from ...models.price_trends_condition_item import PriceTrendsConditionItem
from ...models.price_trends_days import check_price_trends_days
from ...models.price_trends_days import PriceTrendsDays
from ...models.price_trends_form_factor_type_0 import check_price_trends_form_factor_type_0
from ...models.price_trends_form_factor_type_0 import PriceTrendsFormFactorType0
from ...models.price_trends_intended_use_type_0 import check_price_trends_intended_use_type_0
from ...models.price_trends_intended_use_type_0 import PriceTrendsIntendedUseType0
from ...models.price_trends_interface_type_0 import check_price_trends_interface_type_0
from ...models.price_trends_interface_type_0 import PriceTrendsInterfaceType0
from ...models.price_trends_media_type_type_0 import check_price_trends_media_type_type_0
from ...models.price_trends_media_type_type_0 import PriceTrendsMediaTypeType0
from ...models.price_trends_recording_type_type_0 import check_price_trends_recording_type_type_0
from ...models.price_trends_recording_type_type_0 import PriceTrendsRecordingTypeType0
from ...models.trends import Trends
from ...types import UNSET, Unset
from typing import cast
from typing import Literal, cast



def _get_kwargs(
    *,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[PriceTrendsConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PriceTrendsMediaTypeType0 | Unset = UNSET,
    form_factor: None | PriceTrendsFormFactorType0 | Unset = UNSET,
    interface: None | PriceTrendsInterfaceType0 | Unset = UNSET,
    recording_type: None | PriceTrendsRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset = UNSET,
    days: PriceTrendsDays | Unset = 90,
    by: None | PriceTrendsByType0 | Unset = UNSET,
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

    json_days: int | Unset = UNSET
    if not isinstance(days, Unset):
        json_days = days

    params["days"] = json_days

    json_by: None | str | Unset
    if isinstance(by, Unset):
        json_by = UNSET
    elif isinstance(by, str):
        json_by = by
    else:
        json_by = by
    params["by"] = json_by

    params["recent_days"] = recent_days


    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}


    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/trends",
        "params": params,
    }


    return _kwargs



def _parse_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> HTTPValidationError | Trends | None:
    if response.status_code == 200:
        response_200 = Trends.from_dict(response.json())



        return response_200

    if response.status_code == 422:
        response_422 = HTTPValidationError.from_dict(response.json())



        return response_422

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(*, client: AuthenticatedClient | Client, response: httpx.Response) -> Response[HTTPValidationError | Trends]:
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
    condition: list[PriceTrendsConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PriceTrendsMediaTypeType0 | Unset = UNSET,
    form_factor: None | PriceTrendsFormFactorType0 | Unset = UNSET,
    interface: None | PriceTrendsInterfaceType0 | Unset = UNSET,
    recording_type: None | PriceTrendsRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset = UNSET,
    days: PriceTrendsDays | Unset = 90,
    by: None | PriceTrendsByType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | Trends]:
    """ Read market price trends

     The typical item price per terabyte on each day of a period, over the drives asked for
    (every drive, or narrowed by the same filters as the drives list) and over each condition,
    capacity or store when asked. recent_days: an offer unchecked for longer
    is taken to have ended at its last check. Only drives priced at the opening of the period
    are followed, so new arrivals do not move the historical line. A day with no available
    prices has no point. Item prices exclude shipping. Market values are cents per decimal TB;
    when split by store, part values are hundredths of a percent above the typical price of
    shared drives. Results are recalculated when relevant data changes or a new UTC day begins.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PriceTrendsConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PriceTrendsMediaTypeType0 | Unset):
        form_factor (None | PriceTrendsFormFactorType0 | Unset):
        interface (None | PriceTrendsInterfaceType0 | Unset):
        recording_type (None | PriceTrendsRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset):
        days (PriceTrendsDays | Unset): How far back to look, in days. Default: 90.
        by (None | PriceTrendsByType0 | Unset):
        recent_days (int | Unset): An offer unchecked for longer is treated as ending at its last
            check. Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Trends]
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
days=days,
by=by,
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
    condition: list[PriceTrendsConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PriceTrendsMediaTypeType0 | Unset = UNSET,
    form_factor: None | PriceTrendsFormFactorType0 | Unset = UNSET,
    interface: None | PriceTrendsInterfaceType0 | Unset = UNSET,
    recording_type: None | PriceTrendsRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset = UNSET,
    days: PriceTrendsDays | Unset = 90,
    by: None | PriceTrendsByType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | Trends | None:
    """ Read market price trends

     The typical item price per terabyte on each day of a period, over the drives asked for
    (every drive, or narrowed by the same filters as the drives list) and over each condition,
    capacity or store when asked. recent_days: an offer unchecked for longer
    is taken to have ended at its last check. Only drives priced at the opening of the period
    are followed, so new arrivals do not move the historical line. A day with no available
    prices has no point. Item prices exclude shipping. Market values are cents per decimal TB;
    when split by store, part values are hundredths of a percent above the typical price of
    shared drives. Results are recalculated when relevant data changes or a new UTC day begins.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PriceTrendsConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PriceTrendsMediaTypeType0 | Unset):
        form_factor (None | PriceTrendsFormFactorType0 | Unset):
        interface (None | PriceTrendsInterfaceType0 | Unset):
        recording_type (None | PriceTrendsRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset):
        days (PriceTrendsDays | Unset): How far back to look, in days. Default: 90.
        by (None | PriceTrendsByType0 | Unset):
        recent_days (int | Unset): An offer unchecked for longer is treated as ending at its last
            check. Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Trends
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
days=days,
by=by,
recent_days=recent_days,

    ).parsed

async def asyncio_detailed(
    *,
    client: AuthenticatedClient | Client,
    q: str | Unset = '',
    brand: list[str] | Unset = UNSET,
    capacity: list[int] | Unset = UNSET,
    condition: list[PriceTrendsConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PriceTrendsMediaTypeType0 | Unset = UNSET,
    form_factor: None | PriceTrendsFormFactorType0 | Unset = UNSET,
    interface: None | PriceTrendsInterfaceType0 | Unset = UNSET,
    recording_type: None | PriceTrendsRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset = UNSET,
    days: PriceTrendsDays | Unset = 90,
    by: None | PriceTrendsByType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> Response[HTTPValidationError | Trends]:
    """ Read market price trends

     The typical item price per terabyte on each day of a period, over the drives asked for
    (every drive, or narrowed by the same filters as the drives list) and over each condition,
    capacity or store when asked. recent_days: an offer unchecked for longer
    is taken to have ended at its last check. Only drives priced at the opening of the period
    are followed, so new arrivals do not move the historical line. A day with no available
    prices has no point. Item prices exclude shipping. Market values are cents per decimal TB;
    when split by store, part values are hundredths of a percent above the typical price of
    shared drives. Results are recalculated when relevant data changes or a new UTC day begins.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PriceTrendsConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PriceTrendsMediaTypeType0 | Unset):
        form_factor (None | PriceTrendsFormFactorType0 | Unset):
        interface (None | PriceTrendsInterfaceType0 | Unset):
        recording_type (None | PriceTrendsRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset):
        days (PriceTrendsDays | Unset): How far back to look, in days. Default: 90.
        by (None | PriceTrendsByType0 | Unset):
        recent_days (int | Unset): An offer unchecked for longer is treated as ending at its last
            check. Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[HTTPValidationError | Trends]
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
days=days,
by=by,
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
    condition: list[PriceTrendsConditionItem] | Unset = UNSET,
    store: list[str] | Unset = UNSET,
    media_type: None | PriceTrendsMediaTypeType0 | Unset = UNSET,
    form_factor: None | PriceTrendsFormFactorType0 | Unset = UNSET,
    interface: None | PriceTrendsInterfaceType0 | Unset = UNSET,
    recording_type: None | PriceTrendsRecordingTypeType0 | Unset = UNSET,
    intended_use: Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset = UNSET,
    days: PriceTrendsDays | Unset = 90,
    by: None | PriceTrendsByType0 | Unset = UNSET,
    recent_days: int | Unset = 7,

) -> HTTPValidationError | Trends | None:
    """ Read market price trends

     The typical item price per terabyte on each day of a period, over the drives asked for
    (every drive, or narrowed by the same filters as the drives list) and over each condition,
    capacity or store when asked. recent_days: an offer unchecked for longer
    is taken to have ended at its last check. Only drives priced at the opening of the period
    are followed, so new arrivals do not move the historical line. A day with no available
    prices has no point. Item prices exclude shipping. Market values are cents per decimal TB;
    when split by store, part values are hundredths of a percent above the typical price of
    shared drives. Results are recalculated when relevant data changes or a new UTC day begins.

    Args:
        q (str | Unset): Words in a title, MPN or seller Default: ''.
        brand (list[str] | Unset): Brands, unknown for none named
        capacity (list[int] | Unset): Capacity choices in decimal GB. Repeat the parameter for
            multiple choices.
        condition (list[PriceTrendsConditionItem] | Unset): Condition choices; repeat the
            parameter for multiple choices.
        store (list[str] | Unset): Source keys, not UUIDs; repeat for multiple stores.
        media_type (None | PriceTrendsMediaTypeType0 | Unset):
        form_factor (None | PriceTrendsFormFactorType0 | Unset):
        interface (None | PriceTrendsInterfaceType0 | Unset):
        recording_type (None | PriceTrendsRecordingTypeType0 | Unset):
        intended_use (Literal['unknown'] | None | PriceTrendsIntendedUseType0 | Unset):
        days (PriceTrendsDays | Unset): How far back to look, in days. Default: 90.
        by (None | PriceTrendsByType0 | Unset):
        recent_days (int | Unset): An offer unchecked for longer is treated as ending at its last
            check. Default: 7.

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        HTTPValidationError | Trends
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
days=days,
by=by,
recent_days=recent_days,

    )).parsed
