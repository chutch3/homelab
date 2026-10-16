"""The kinds of store disktracker knows, and what each needs to know about a store: its settings,
written once, as the fields of a model. Each field says how the Admin form asks for it and how it
is checked; the collector's client is generated from these models, so it reads a store's settings
as they are written here."""

import re
from dataclasses import asdict, dataclass
from typing import Annotated, Any, ClassVar, Literal

from pydantic import ConfigDict, ValidationError
from pydantic_core import InitErrorDetails, PydanticCustomError

from disktracker.contract import Contract

SettingType = Literal["text", "list", "flag"]
# What a setting is when nothing is entered for it.
BLANK: dict[SettingType, Any] = {"text": "", "list": [], "flag": False}


@dataclass(frozen=True)
class Setting:
    """How the Admin form asks for a setting and how it is checked. A text left blank is "", a
    list is empty, a flag is off; required means it cannot be left so."""

    label: str
    required: bool = False
    description: str = ""
    placeholder: str = ""
    # The group of settings it is asked for among; "" for none.
    group: str = ""
    # What a text must look like, and what to say when it does not. Every setting with a
    # pattern says how it should look.
    pattern: str = ""
    pattern_message: str = ""
    # The text is itself a regular expression; capturing, one with a group.
    regex: bool = False
    capturing: bool = False
    # Another setting that, once given, makes this one required.
    needs: str = ""


@dataclass(frozen=True)
class Group:
    """Settings asked for together, apart from the rest, with what they are for."""

    name: str
    label: str
    help: str


def complaint(kind: SettingType, setting: Setting, value: Any, given: dict[str, Any]) -> str | None:
    """What is wrong with one setting's value; None when nothing is."""
    if kind == "flag":
        return None if isinstance(value, bool) else "Choose yes or no."
    if kind == "list":
        if not isinstance(value, list) or not all(isinstance(entry, str) for entry in value):
            return "Enter a list."
        entered = [entry for entry in value if entry.strip()]
        return "Enter at least one." if setting.required and not entered else None
    if not isinstance(value, str):
        return "Enter text."
    if not value:
        if setting.required:
            return "Enter this."
        needed = setting.needs and given.get(setting.needs)
        return "Say which this is: the settings beside it need it." if needed else None
    if setting.pattern and not re.search(setting.pattern, value):
        return setting.pattern_message
    if setting.regex:
        try:
            groups = re.compile(value).groups
        except re.error as error:
            return f"Enter a regular expression ({error})."
        if setting.capturing and groups < 1:
            return "Put a group, ( ), around the data."
    return None


class Settings(Contract):
    """A kind of store's settings. A store's settings are checked against them as it is saved
    (checked); as it is read back, they are only filled in, so the collector never has to guess
    a default."""

    # Read back, every setting is given, so the schema of what is read says each is there.
    model_config = ConfigDict(extra="forbid")
    groups: ClassVar[tuple[Group, ...]] = ()

    @classmethod
    def described(cls) -> list[tuple[str, SettingType, Setting]]:
        """Each setting's name, type, and how it is asked for, in order."""
        types: dict[Any, SettingType] = {str: "text", list[str]: "list", bool: "flag"}
        return [
            (
                name,
                types[field.annotation],
                next(m for m in field.metadata if isinstance(m, Setting)),
            )
            for name, field in cls.model_fields.items()
        ]

    @classmethod
    def checked(cls, entered: Any) -> dict[str, Any]:
        """The settings entered for a store, each checked, and any left out given as blank."""
        if not isinstance(entered, dict):
            raise PydanticCustomError("dict_type", "Enter the settings.")
        described = {name: (kind, setting) for name, kind, setting in cls.described()}
        errors = [
            InitErrorDetails(
                type=PydanticCustomError(
                    "extra_forbidden", "This kind of store has no such setting."
                ),
                loc=(name,),
                input=value,
            )
            for name, value in entered.items()
            if name not in described
        ]
        given = {name: entered.get(name, BLANK[kind]) for name, (kind, _) in described.items()}
        for name, (kind, setting) in described.items():
            wrong = complaint(kind, setting, given[name], given)
            if wrong:
                errors.append(
                    InitErrorDetails(
                        type=PydanticCustomError("value_error", wrong),
                        loc=(name,),
                        input=given[name],
                    )
                )
        if errors:
            raise ValidationError.from_exception_data("settings", errors)
        return given

    @classmethod
    def saved(cls, saved: dict[str, Any]) -> dict[str, Any]:
        """A store's saved settings, as its kind has them now: without any dropped since. Those
        added since are left to their blanks."""
        return {name: value for name, value in saved.items() if name in cls.model_fields}


def path(label: str, placeholder: str, description: str = "", needs: str = "") -> Setting:
    """A setting that says where something is in the data a page carries: a path."""
    return Setting(
        label,
        group="data",
        placeholder=placeholder,
        description=description,
        needs=needs,
        pattern=r"^\S{0,200}$",
        pattern_message="A path has no spaces in it.",
    )


SITEMAP_PATH = Setting(
    "Sitemap path",
    placeholder="/sitemap.xml",
    description="Blank: the sitemap robots.txt names, or /sitemap.xml",
    pattern=r"^(/\S*)?$",
    pattern_message="Start it with /.",
)


class ManualSettings(Settings):
    """A store entered by hand has nothing to set."""


class ShopifySettings(Settings):
    collections: Annotated[
        list[str],
        Setting(
            "Collections",
            required=True,
            placeholder="hard-drives, solid-state-drives",
            description="Comma-separated collection handles",
        ),
    ] = []
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

    sitemap_path: Annotated[str, SITEMAP_PATH] = ""
    product_path_pattern: Annotated[
        str,
        Setting(
            "Product path pattern",
            placeholder="-p/",
            description="A regular expression product page paths match; blank reads every page",
            regex=True,
        ),
    ] = ""
    free_shipping_marker: Annotated[
        str, Setting("Free-shipping marker", description="Text on a page whose item ships free")
    ] = ""
    data_pattern: Annotated[
        str,
        Setting(
            "Data pattern",
            group="data",
            placeholder=r"product_models = JSON\.parse\('(.*?)'\);",
            description="A regular expression whose ( ) holds the JSON the page carries its"
            " products in",
            regex=True,
            capturing=True,
        ),
    ] = ""
    data_items: Annotated[
        str,
        path(
            "Products path",
            "*.skus.*",
            "Where the products are in that JSON: names apart by dots, * for every entry of a"
            " list; blank when it is one product",
        ),
    ] = ""
    data_model_field: Annotated[
        str, path("Model number field", "modelNo", needs="data_pattern")
    ] = ""
    data_name_field: Annotated[
        str,
        path(
            "Name field",
            "name",
            "The capacity and condition are read from the name",
            needs="data_pattern",
        ),
    ] = ""
    data_price_field: Annotated[
        str,
        path(
            "Price field",
            "final_price",
            "A product without a price is not an offer",
            needs="data_pattern",
        ),
    ] = ""
    data_brand_field: Annotated[
        str, path("Brand field", "brand", "Who made it, for names that do not say")
    ] = ""
    data_stock_field: Annotated[
        str, path("Stock field", "stock_status", "Blank: in stock whenever it has a price")
    ] = ""
    data_in_stock_value: Annotated[
        str, Setting("In-stock value", group="data", placeholder="IN_STOCK")
    ] = ""


class SapCommerceSettings(Settings):
    api_url: Annotated[
        str,
        Setting(
            "API URL",
            required=True,
            placeholder="https://api.example.com/occ/v2",
            pattern=r"^https?://[^\s/]+\S*$",
            pattern_message="Enter the API's address, starting http:// or https://.",
        ),
    ] = ""
    site: Annotated[str, Setting("Site", required=True, placeholder="us")] = ""
    sitemap_path: Annotated[str, SITEMAP_PATH] = ""
    product_path_pattern: Annotated[
        str,
        Setting(
            "Product path pattern",
            placeholder="^/products/",
            description="A regular expression the product pages to read match; blank reads"
            " every page",
            regex=True,
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
                {"name": name, "type": kind, **asdict(setting)}
                for name, kind, setting in self.settings.described()
            ],
        }


KINDS: dict[str, Kind] = {
    "sap_commerce": Kind("SAP Commerce", SapCommerceSettings),
    "shopify": Kind("Shopify", ShopifySettings),
    "sitemap": Kind("Sitemap + product page", SitemapSettings, page_test=True),
    "manual": Kind("Entered by hand", ManualSettings, collected=False),
}
