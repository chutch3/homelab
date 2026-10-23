"""The kinds of store disktracker knows, and what each needs to know about a store: its settings,
written once, as the fields of a model. Each model holds its own rules, as Pydantic fields and
validators; each field's Setting says only how the Admin form asks for it. The collector's client
is generated from these models, so it reads a store's settings as they are written here."""

import re
from dataclasses import asdict, dataclass
from typing import Annotated, Any, ClassVar, Literal

from pydantic import (
    AfterValidator,
    AnyHttpUrl,
    BeforeValidator,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    ValidationInfo,
    field_validator,
)

from disktracker.contract import Contract

SettingType = Literal["text", "list", "flag"]

# Checked as a URL, kept as entered: Pydantic's URL would add a trailing slash to a bare host.
_HTTP_URL = TypeAdapter(AnyHttpUrl)


@dataclass(frozen=True)
class Setting:
    """How the Admin form asks for a setting: what it is called and what helps fill it in, and
    the group of settings it is asked for among ("" for none). Its rules are its field's."""

    label: str
    description: str = ""
    placeholder: str = ""
    group: str = ""


@dataclass(frozen=True)
class Group:
    """Settings asked for together, apart from the rest, with what they are for."""

    name: str
    label: str
    help: str


def _entered(value: Any) -> Any:
    """A list's entries, without those left blank."""
    if isinstance(value, list):
        return [entry for entry in value if not isinstance(entry, str) or entry.strip()]
    return value


def _sitemap_path(value: str) -> str:
    if value and not value.startswith("/") or re.search(r"\s", value):
        raise ValueError("Start it with /.")
    return value


def _regex(value: str) -> str:
    try:
        re.compile(value)
    except re.error as error:
        raise ValueError(f"Enter a regular expression ({error}).") from error
    return value


def _path(value: str) -> str:
    if not re.fullmatch(r"\S{0,200}", value):
        raise ValueError("A path has no spaces in it.")
    return value


def _address(value: str) -> str:
    try:
        _HTTP_URL.validate_python(value)
    except ValidationError as error:
        raise ValueError("Enter the API's address, starting http:// or https://.") from error
    return value


# A list at least one entry of which is needed, blank entries being none.
Entries = Annotated[list[str], BeforeValidator(_entered), Field(min_length=1)]
SitemapPath = Annotated[str, AfterValidator(_sitemap_path)]
Pattern = Annotated[str, AfterValidator(_regex)]
Path = Annotated[str, AfterValidator(_path)]


class Settings(Contract):
    """A kind of store's settings, holding to their rules however they are read."""

    model_config = ConfigDict(extra="forbid")
    groups: ClassVar[tuple[Group, ...]] = ()

    @classmethod
    def described(cls) -> list[tuple[str, SettingType, Setting, bool]]:
        """Each setting's name, type, how it is asked for, and whether it must be given, in
        order."""
        types: dict[Any, SettingType] = {str: "text", list[str]: "list", bool: "flag"}
        return [
            (
                name,
                types[field.annotation],
                next(m for m in field.metadata if isinstance(m, Setting)),
                field.is_required(),
            )
            for name, field in cls.model_fields.items()
        ]

    @classmethod
    def saved(cls, saved: dict[str, Any]) -> dict[str, Any]:
        """A store's saved settings, as its kind has them now: without any dropped since. Those
        added since are left to their defaults."""
        return {name: value for name, value in saved.items() if name in cls.model_fields}


SITEMAP_PATH = Setting(
    "Sitemap path",
    placeholder="/sitemap.xml",
    description="Blank: the sitemap robots.txt names, or /sitemap.xml",
)


def path(label: str, placeholder: str, description: str = "") -> Setting:
    """How the form asks where something is in the data a page carries."""
    return Setting(label, group="data", placeholder=placeholder, description=description)


class ManualSettings(Settings):
    """A store entered by hand has nothing to set."""


class ShopifySettings(Settings):
    collections: Annotated[
        Entries,
        Setting(
            "Collections",
            placeholder="hard-drives, solid-state-drives",
            description="Comma-separated collection handles",
        ),
    ]
    free_shipping: Annotated[bool, Setting("Every order ships free")] = False


class SitemapSettings(Settings):
    groups = (
        Group(
            "data",
            "Pages that list several products",
            "For a store whose page covers a whole family of drives and carries them as JSON"
            " inside a script. Left blank, each page is one product, read from its own price"
            " markup.",
        ),
    )

    sitemap_path: Annotated[SitemapPath, SITEMAP_PATH] = ""
    product_path_pattern: Annotated[
        Pattern,
        Setting(
            "Product path pattern",
            placeholder="-p/",
            description="A regular expression product page paths match; blank reads every page",
        ),
    ] = ""
    free_shipping_marker: Annotated[
        str, Setting("Free-shipping marker", description="Text on a page whose item ships free")
    ] = ""
    data_pattern: Annotated[
        Pattern,
        Setting(
            "Data pattern",
            group="data",
            placeholder=r"product_models = JSON\.parse\('(.*?)'\);",
            description="A regular expression whose ( ) holds the JSON the page carries its"
            " products in",
        ),
    ] = ""
    data_items: Annotated[
        Path,
        path(
            "Products path",
            "*.skus.*",
            "Where the products are in that JSON: names apart by dots, * for every entry of a"
            " list; blank when it is one product",
        ),
    ] = ""
    # Needed once there is data to read: validated even when left out.
    data_model_field: Annotated[Path, path("Model number field", "modelNo")] = Field(
        default="", validate_default=True
    )
    data_name_field: Annotated[
        Path, path("Name field", "name", "The capacity and condition are read from the name")
    ] = Field(default="", validate_default=True)
    data_price_field: Annotated[
        Path, path("Price field", "final_price", "A product without a price is not an offer")
    ] = Field(default="", validate_default=True)
    data_brand_field: Annotated[
        Path, path("Brand field", "brand", "Who made it, for names that do not say")
    ] = ""
    data_stock_field: Annotated[
        Path, path("Stock field", "stock_status", "Blank: in stock whenever it has a price")
    ] = ""
    data_in_stock_value: Annotated[
        str, Setting("In-stock value", group="data", placeholder="IN_STOCK")
    ] = ""

    @field_validator("data_pattern")
    @classmethod
    def a_group_around_the_data(cls, value: str) -> str:
        if value and re.compile(value).groups < 1:
            raise ValueError("Put a group, ( ), around the data.")
        return value

    @field_validator("data_model_field", "data_name_field", "data_price_field")
    @classmethod
    def said_when_there_is_data(cls, value: str, info: ValidationInfo) -> str:
        if not value and info.data.get("data_pattern"):
            raise ValueError("Say which this is: the settings beside it need it.")
        return value


class SapCommerceSettings(Settings):
    api_url: Annotated[
        str,
        AfterValidator(_address),
        Setting("API URL", placeholder="https://api.example.com/occ/v2"),
    ]
    site: Annotated[str, Field(min_length=1), Setting("Site", placeholder="us")]
    sitemap_path: Annotated[SitemapPath, SITEMAP_PATH] = ""
    product_path_pattern: Annotated[
        Pattern,
        Setting(
            "Product path pattern",
            placeholder="^/products/",
            description="A regular expression the product pages to read match; blank reads"
            " every page",
        ),
    ] = ""
    # Put before a recertified product's SKU; dropped to find its model or part number.
    recertified_sku_prefix: Annotated[
        str,
        Setting(
            "Recertified SKU prefix",
            placeholder="R",
            description="Put before a recertified product's SKU",
        ),
    ] = ""


@dataclass(frozen=True)
class Kind:
    """A kind of store: what it is called, its settings, whether the collector reads it, and
    whether one of its pages can be read alone to test it."""

    label: str
    settings: type[Settings]
    collected: bool = True
    page_test: bool = False

    def described(self) -> dict[str, Any]:
        """The kind as the Admin form is drawn from it."""
        return {
            "label": self.label,
            "collected": self.collected,
            "page_test": self.page_test,
            "groups": [asdict(group) for group in self.settings.groups],
            "settings": [
                {"name": name, "type": kind, "required": required, **asdict(setting)}
                for name, kind, setting, required in self.settings.described()
            ],
        }


KINDS: dict[str, Kind] = {
    "sap_commerce": Kind("SAP Commerce", SapCommerceSettings),
    "shopify": Kind("Shopify", ShopifySettings),
    "sitemap": Kind("Sitemap + product page", SitemapSettings, page_test=True),
    "manual": Kind("Entered by hand", ManualSettings, collected=False),
}
