"""A store with no API whose sitemap lists every product page, and whose pages give price and
stock in schema.org terms: as tags in the markup (goHardDrive, on Volusion) or else as a JSON-LD
Product (ServerOrbit, on CS-Cart). The page title carries the MPN, capacity and condition.

The sitemap is the one at sitemap_path, or the ones robots.txt names, or /sitemap.xml. Only
URLs whose path matches product_path_pattern (every URL when it is blank) are product pages, and
pages for things that are merely for drives are skipped by name. When most product URLs name a
capacity ("12TB-"), as goHardDrive's do, the ones that do not are skipped too, which leaves out
most accessories without a request.

A page's title is its og:title (else its <title>), which carries no store name. Drives are
matched across stores by the manufacturer's MPN: the one the title has, else the part number
the page's JSON-LD states (its mpn, or its sku when the title has that same text). A drive of a store brand,
or sold as white label ("WL", "White Label", "Major Brand"), has none and is sold nowhere else,
so it goes by the store's product code, the last part of its page's path; any other drive whose
MPN cannot be read goes to the Review queue instead of a code no other store would share.

Non-new items say so in the title ("(Certified Refurbished)"), read by disktracker's condition
rules; a title without a condition is a new item. An item ships free when its page contains
free_shipping_marker; otherwise shipping is unknown.

A store whose pages each carry a whole family as data inside a script (Seagate) is read from
that data instead, when the source says where it is (the data_ settings): one offer for each
model the data prices, named and numbered as the data has it, all at the page's URL. Its maker
is the one its name gives, else the one the data's brand field gives."""

import html
import json
import logging
import re
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, fields, replace
from decimal import Decimal
from functools import cached_property
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import urlsplit

from listing_text.readers import (
    STORE_BRANDS,
    capacity_in,
    condition_in,
    maker_named,
    mpn_from_title,
    specifications_in_title,
)

from collector.errors import OutOfTime, SourceUnavailable
from collector.models import FREE_SHIPPING, TITLE_LIMIT, ScrapedOffer, Store
from collector.polite import Pages, same_site
from collector.ports import (
    Fact,
    Group,
    Inspection,
    Reading,
    Rechecked,
    Site,
    Tell,
    tell_nobody,
)
from collector.settings import described, setting, settings_from
from collector.sources.rechecking import rechecked
from collector.sources.sitemaps import SAMPLE_PAGES, each_fetched, locations, page_urls
from disktracker_api.models import ListingSummary

log = logging.getLogger(__name__)
NOT_DRIVES = re.compile(
    r"enclosure|dock|adapter|cable|caddy|tray|bracket|duplicator|kvm|monitor|keyboard|lcd"
    # Memory modules have a capacity too. "Memory" alone is left out: drives are flash memory.
    r"|\bddr\d|dimm\b|\bram\b",
    re.IGNORECASE,
)
# A capacity as written in a product URL: "12TB-", "500G-".
URL_CAPACITY = re.compile(r"(?<![a-z0-9])\d+(\.\d+)?(tb|gb|t|g)(?![a-z])", re.IGNORECASE)
JSON_LD = re.compile(
    r"<script[^>]*type=['\"]application/ld\+json['\"][^>]*>(.*?)</script>",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class EmbeddedData:
    """Where a page carries its products as JSON inside a script, and which of each product's
    fields say what. pattern's first group is the JSON; items is the path to the products
    within it, and each field a path within a product: names apart by dots, * for every entry
    of a list. A product is in stock when its stock field has in_stock_value, or, with no stock
    field, whenever it has a price."""

    pattern: re.Pattern[str]
    items: str
    model_field: str
    name_field: str
    price_field: str
    # Who made it, for products whose name does not say; blank when the data has no such field.
    brand_field: str
    stock_field: str
    in_stock_value: str

    @classmethod
    def of(cls, settings: Mapping[str, Any]) -> "EmbeddedData | None":
        named = {name: settings[f"data_{name}"] for name in cls.__dataclass_fields__}
        if not named["pattern"]:
            return None
        pattern = re.compile(named["pattern"], re.DOTALL)
        if pattern.groups < 1:
            raise ValueError("data_pattern needs a group around the data")
        return cls(**{**named, "pattern": pattern})


def in_the_data(label: str, placeholder: str, description: str = "", needs: str = "") -> Any:
    """A setting that says where something is in the data a page carries: a path."""
    return setting(
        label,
        group="data",
        placeholder=placeholder,
        description=description,
        needs=needs,
        pattern=r"^\S{0,200}$",
        pattern_message="A path has no spaces in it.",
    )


@dataclass(frozen=True)
class SitemapSettings:
    sitemap_path: str = setting(
        "Sitemap path",
        placeholder="/sitemap.xml",
        description="Blank: the sitemap robots.txt names, or /sitemap.xml",
        pattern=r"^(/\S*)?$",
        pattern_message="Start it with /.",
    )
    product_path_pattern: str = setting(
        "Product path pattern",
        placeholder="-p/",
        description="A regular expression product page paths match; blank reads every page",
        regex=True,
    )
    free_shipping_marker: str = setting(
        "Free-shipping marker", description="Text on a page whose item ships free"
    )
    data_pattern: str = setting(
        "Data pattern",
        group="data",
        placeholder=r"product_models = JSON\.parse\('(.*?)'\);",
        description="A regular expression whose ( ) holds the JSON the page carries its products"
        " in",
        regex=True,
        capturing=True,
    )
    data_items: str = in_the_data(
        "Products path",
        "*.skus.*",
        "Where the products are in that JSON: names apart by dots, * for every entry of a list;"
        " blank when it is one product",
    )
    data_model_field: str = in_the_data("Model number field", "modelNo", needs="data_pattern")
    data_name_field: str = in_the_data(
        "Name field",
        "name",
        "The capacity and condition are read from the name",
        needs="data_pattern",
    )
    data_price_field: str = in_the_data(
        "Price field",
        "final_price",
        "A product without a price is not an offer",
        needs="data_pattern",
    )
    data_brand_field: str = in_the_data(
        "Brand field", "brand", "Who made it, for names that do not say"
    )
    data_stock_field: str = in_the_data(
        "Stock field", "stock_status", "Blank: in stock whenever it has a price"
    )
    data_in_stock_value: str = setting("In-stock value", group="data", placeholder="IN_STOCK")

    def __post_init__(self) -> None:
        # Patterns that are no regular expression are refused when the settings are read.
        _ = self.product_path, self.data

    @classmethod
    def of(cls, saved: Mapping[str, Any]) -> "SitemapSettings":
        return settings_from(cls, saved)

    @cached_property
    def product_path(self) -> re.Pattern[str]:
        return re.compile(self.product_path_pattern)

    @cached_property
    def data(self) -> EmbeddedData | None:
        """Where its pages carry their products as data; None when each page is one product,
        read from its price tags or JSON-LD."""
        return EmbeddedData.of(asdict(self))


@dataclass(frozen=True)
class Item:
    """One product a page offers. model, brand and condition: its model number, who made it
    and the condition it is in, where the page's data states them."""

    title: str
    price_cents: int | None
    in_stock: bool
    model: str | None = None
    brand: str = ""
    condition: str = ""


def worth_fetching(paths: list[str]) -> list[str]:
    """The product paths that name nothing merely for drives; and, when most of them name a
    capacity, only those that do."""
    drives = [path for path in paths if not NOT_DRIVES.search(path)]
    sized = [path for path in drives if URL_CAPACITY.search(path)]
    return sized if len(sized) * 2 >= len(drives) else drives


def product_path(url: str, base_url: str, settings: SitemapSettings) -> str | None:
    """The path of one of this store's product pages, however the host is written."""
    path = urlsplit(url).path
    return path if same_site(url, base_url) and settings.product_path.search(path) else None


def product_paths(urls: list[str], base_url: str, settings: SitemapSettings) -> list[str]:
    """The paths of the store's product pages among the URLs a sitemap lists."""
    return [path for url in urls if (path := product_path(url, base_url, settings)) is not None]


# A sitemap source with nothing set: every setting, blank.
NOTHING_SET = {entry.name: "" for entry in fields(SitemapSettings)}


def cents(price: object) -> int | None:
    """A price written as a plain number, in cents; None for anything else, and for a price of
    nothing, which is how a store writes a product it sells only by quote."""
    text = str(price)
    return int(Decimal(text) * 100) or None if re.fullmatch(r"\d+(\.\d+)?", text) else None


def things_in(data: object) -> Iterator[Any]:
    """Each thing a piece of JSON-LD describes: the thing itself, each of a list of them, or
    each in the @graph of several a page gathers under one heading."""
    if isinstance(data, list):
        for entry in data:
            yield from things_in(entry)
    elif isinstance(data, dict):
        yield data
        yield from things_in(data.get("@graph", []))


def json_ld_product(page: str) -> Mapping[str, Any]:
    """The Product the page's JSON-LD describes, alone or among other things; empty when it
    describes none."""
    for block in JSON_LD.findall(page):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        for thing in things_in(data):
            if str(thing.get("@type")).endswith("Product"):
                product: Mapping[str, Any] = thing
                return product
    return {}


def json_ld_offer(product: Mapping[str, Any]) -> Mapping[str, Any]:
    """The first offer of a JSON-LD product; empty when it makes none."""
    offers = product.get("offers")
    offer = offers[0] if isinstance(offers, list) and offers else offers
    return offer if isinstance(offer, dict) else {}


def stated_condition(product: Mapping[str, Any]) -> str:
    """The condition the page's JSON-LD offer states, as a word the condition rules can read:
    "Refurbished" from https://schema.org/RefurbishedCondition. "" when it states none."""
    stated = json_ld_offer(product).get("itemCondition")
    if not isinstance(stated, str):
        return ""
    return stated.rsplit("/", 1)[-1].removesuffix("Condition")


def price_and_stock(page: str, product: Mapping[str, Any]) -> tuple[int | None, bool]:
    """The price in cents and whether it is in stock: from the tags in the markup when the
    page has them, else from the first offer of its JSON-LD product."""
    tagged = re.search(r"itemprop=['\"]price['\"]\s+content=['\"]([\d.]+)['\"]", page)
    if tagged:
        # Out-of-stock pages leave the availability tag out.
        in_stock = re.search(r"itemprop=['\"]availability['\"]\s+content=['\"]InStock", page)
        price = cents(tagged[1])
        return price, price is not None and bool(in_stock)
    offer = json_ld_offer(product)
    price = cents(offer.get("price"))
    # Written bare ("InStock") or as a schema.org URL.
    return price, price is not None and str(offer.get("availability", "")).endswith("InStock")


# A part number shorter than this cannot be told from other text in a title ("4TB", "SAS").
STATED_PART_LENGTH = 5


def stated_part(product: Mapping[str, Any], title: str) -> str | None:
    """The part number the page's JSON-LD states: its mpn, or its sku when the title has that
    same text. A sku the title does not have is the store's own number for the product."""
    mpn, sku = product.get("mpn"), product.get("sku")
    if isinstance(mpn, str) and mpn.strip():
        return mpn.strip()
    named = isinstance(sku, str) and len(sku) >= STATED_PART_LENGTH and sku.lower() in title.lower()
    return sku if named and isinstance(sku, str) else None


def stated_brand(product: Mapping[str, Any]) -> str:
    """Who the page's JSON-LD says made the product: a Brand with a name, or just the name."""
    brand = product.get("brand")
    name = brand.get("name") if isinstance(brand, dict) else brand
    return name if isinstance(name, str) else ""


def the_page(page: str) -> Item:
    """A page that is one product: its title, its price and stock as it marks them, and its
    part number and maker: the maker's MPN its title has, else the part its JSON-LD states."""
    found = re.search(r'property="og:title"\s+content="([^"]*)"', page) or re.search(
        r"<title>(.*?)</title>", page, re.DOTALL
    )
    title = html.unescape(found[1]).strip() if found else ""
    product = json_ld_product(page)
    price_cents, in_stock = price_and_stock(page, product)
    return Item(
        title,
        price_cents,
        in_stock,
        model=mpn_from_title(title) or stated_part(product, title),
        brand=stated_brand(product),
        condition=stated_condition(product),
    )


JS_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f"}


def js_string(written: str) -> str:
    """What a JavaScript string literal says, given the text between its quotes."""

    def said(escape: re.Match[str]) -> str:
        code = escape[1]
        return chr(int(code[1:], 16)) if len(code) > 1 else JS_ESCAPES.get(code, code)

    return re.sub(r"\\(u[0-9a-fA-F]{4}|x[0-9a-fA-F]{2}|.)", said, written, flags=re.DOTALL)


def entries(value: object) -> list[Any]:
    """Every entry of a JSON list or object; none of anything else."""
    if isinstance(value, dict):
        return list(value.values())
    return value if isinstance(value, list) else []


def within(value: object, path: str) -> list[Any]:
    """Everything a path leads to inside parsed JSON; nothing where it leads nowhere."""
    found = [value]
    for step in filter(None, path.split(".")):
        if step == "*":
            found = [inner for outer in found for inner in entries(outer)]
        else:
            found = [outer[step] for outer in found if isinstance(outer, dict) and step in outer]
    return found


def embedded_items(page: str, data: EmbeddedData) -> list[Item]:
    """The products in the page's embedded data, each as the data names, numbers and prices
    it; none when the page has no such data."""
    found = data.pattern.search(page)
    if not found:
        return []
    # Data handed to JSON.parse('...') is written as a JavaScript string.
    quoted = page[found.start(1) - 1 : found.start(1)] in ("'", '"')
    try:
        parsed = json.loads(js_string(found[1]) if quoted else found[1])
    except ValueError:
        return []

    def said(product: object, field: str) -> str:
        return str(next(iter(within(product, field)), "")) if field else ""

    items = []
    for product in within(parsed, data.items):
        price = cents(said(product, data.price_field))
        stocked = not data.stock_field or said(product, data.stock_field) == data.in_stock_value
        items.append(
            Item(
                title=said(product, data.name_field).strip(),
                price_cents=price,
                in_stock=price is not None and stocked,
                model=said(product, data.model_field).strip() or None,
                brand=said(product, data.brand_field),
            )
        )
    return items


def items_on(page: str, settings: SitemapSettings) -> list[Item]:
    """What a page offers: itself, or each product in its embedded data when the source says
    where that is."""
    return [the_page(page)] if settings.data is None else embedded_items(page, settings.data)


def ships_free(page: str, settings: SitemapSettings) -> bool:
    return bool(settings.free_shipping_marker) and settings.free_shipping_marker in page


def product_code(url: str) -> str:
    """The store's code for a product: the last part of its page's path, without extension."""
    return PurePosixPath(urlsplit(url).path).stem.upper()


# How a title names a drive sold under no maker's name: at its start, or after the store's own
# name where a store leads its titles with that ("goHardDrive.com - WL 150GB ...").
WHITE_LABEL = re.compile(
    r"^\s*(\S+\.\w+\s*-\s*)?(generic\s+)?(wl|white label|major brand)\b", re.IGNORECASE
)


def mpn_for(title: str, url: str) -> str | None:
    """The manufacturer's MPN, which other stores share. A store brand's drive, or one sold as
    white label, has none and is sold nowhere else, so it goes by the store's product code.
    Any other drive without a readable MPN is left for review, whether or not its maker is
    one disktracker knows, rather than given a code that could never match another store."""
    maker = mpn_from_title(title)
    if maker:
        return maker
    own = maker_named(title) in STORE_BRANDS or WHITE_LABEL.search(title)
    return product_code(url) if own else None


def not_a_drive(item: Item) -> str | None:
    """Why an item is no offer of a drive; None when it is one."""
    if item.price_cents is None:
        return "no price"
    if capacity_in(item.title) is None:
        return "no capacity in its name"
    return "named as an accessory" if NOT_DRIVES.search(item.title) else None


def why_no_offers(page: str, settings: SitemapSettings) -> str:
    """Why a page gave no offer, for whoever is setting the source up."""
    items = items_on(page, settings)
    if settings.data is None:
        return f"{not_a_drive(items[0])} ({items[0].title})"
    if not items:
        return "its data pattern or products path matched nothing"
    reasons = Counter(not_a_drive(item) for item in items)
    told = ", ".join(f"{count} with {reason}" for reason, count in reasons.items())
    return f"{len(items)} products in its data: {told}"


def offers_from_page(
    page: str, url: str, store: Store, settings: SitemapSettings
) -> list[ScrapedOffer]:
    """The offers on a product page: one for each drive it prices, none when it is not for
    drives."""
    free = ships_free(page, settings)
    return [
        ScrapedOffer(
            source=store.key,
            url=url,
            title=item.title[:TITLE_LIMIT],
            mpn=item.model or mpn_for(item.title, url),
            brand=maker_named(item.title) or maker_named(item.brand),
            # What the title says of its condition, then what the page's data states of it.
            condition=condition_in(store.conditions, item.title, item.condition) or "new",
            capacity_gb=capacity_in(item.title),
            item_price_cents=item.price_cents,
            in_stock=item.in_stock,
            shipping_cents=FREE_SHIPPING if free else None,
            specifications=specifications_in_title(item.title),
        )
        for item in items_on(page, settings)
        if not_a_drive(item) is None
    ]


def known_item(listing: ListingSummary, page: str, settings: SitemapSettings) -> Item | None:
    """A known offer's product as its page has it now: the page itself, or, on a page of many,
    the one with the offer's model number."""
    items = items_on(page, settings)
    if settings.data is None:
        return items[0]
    return next((item for item in items if (item.model or "").upper() == listing.mpn), None)


def recheck_offer(
    listing: ListingSummary, page: str | None, store: Store, settings: SitemapSettings
) -> ScrapedOffer:
    """A known offer as its product page shows it now (None when the page is gone)."""
    found = known_item(listing, page, settings) if page is not None else None
    return ScrapedOffer.recheck(
        listing,
        source=store.key,
        item_price_cents=found.price_cents if found else None,
        in_stock=bool(found and found.in_stock),
        shipping_cents=FREE_SHIPPING if page and found and ships_free(page, settings) else None,
    )


# --- Telling a store of this kind from one of its pages, and working out its settings. These
# are guesses to be tried, not facts: each is checked by reading the page with it.

# Data handed to JSON.parse as a string, and the name it is given: x.models = JSON.parse('…');
PARSED = re.compile(r"([A-Za-z_$][\w$]*)\s*=\s*JSON\.parse\('((?:[^'\\]|\\.)*)'\)\s*;")
# How deep into a page's data its products are looked for.
DEPTH = 6
PART_NUMBER = re.compile(r"[A-Za-z0-9][A-Za-z0-9/._-]{4,}")
IN_STOCK = re.compile(r"in[ _-]?stock|available", re.IGNORECASE)
# What a field's name says it holds, most telling first.
PRICE_NAMES = (
    r"final|sale|special|current",
    r"^price$",
    r"^(?!.*(regular|list|msrp|old|was|compare|original))",
    r"",
)
MODEL_NAMES = (r"mpn", r"model", r"part", r"sku")
NAME_NAMES = (r"^(name|title)$", r"name|title")
BRAND_NAMES = (r"brand", r"manufacturer", r"vendor")


def literal(text: str) -> str:
    """Text as a regular expression that matches just it, written as a person would: a hyphen
    or a space outside brackets needs no escape."""
    return re.escape(text).replace(r"\-", "-").replace(r"\ ", " ")


def blobs(page: str) -> Iterator[tuple[str, str]]:
    """Each piece of JSON a script hands the page to parse: a pattern that finds it, and its
    text, written as a JavaScript string."""
    for found in PARSED.finditer(page):
        yield rf"{literal(found[1])} = JSON\.parse\('(.*?)'\);", found[2]


def collections(nodes: list[Any], path: tuple[str, ...] = ()) -> Iterator[tuple[str, list[Any]]]:
    """Every set of objects in parsed JSON that a products path could lead to, with that path."""
    objects = [node for node in nodes if isinstance(node, dict)]
    if objects:
        yield ".".join(path), objects
    if len(path) >= DEPTH:
        return
    entries = [entry for node in nodes if isinstance(node, list) for entry in node]
    if entries:
        yield from collections(entries, (*path, "*"))
    for key in dict.fromkeys(key for node in objects for key in node):
        yield from collections([node[key] for node in objects if key in node], (*path, key))


def named(objects: list[Any], names: tuple[str, ...], holds: Any, within: str = "") -> str:
    """The field, by what its name says, that holds such a value in some object; "" if none.
    within: text the field's name must have, whatever else it says."""
    keys = [
        key
        for key in dict.fromkeys(key for item in objects for key in item)
        if within in key.lower()
    ]
    for name in names:
        for key in keys:
            if re.search(name, key, re.IGNORECASE) and any(
                holds(item.get(key)) for item in objects
            ):
                return str(key)
    return ""


def is_part_number(value: object) -> bool:
    return (
        isinstance(value, str)
        and bool(PART_NUMBER.fullmatch(value.strip()))
        and any(character.isdigit() for character in value)
    )


def stock_field(objects: list[Any]) -> tuple[str, str]:
    """The field that says a product is in stock, and how it says it: the value written most
    like a code ("IN_STOCK" before "In Stock"). ("", "") when the data does not say."""
    said = [
        (key, str(value))
        for item in objects
        for key, value in item.items()
        if re.search(r"stock|availab", key, re.IGNORECASE)
        and isinstance(value, str)
        and IN_STOCK.fullmatch(value.strip())
    ]
    return min(said, key=lambda pair: (" " in pair[1], len(pair[0])), default=("", ""))


def fields_of(objects: list[Any]) -> dict[str, str] | None:
    """Which field of these objects is a product's price, name and model number, if they are
    products at all, and its brand and stock where they say."""
    price = named(objects, PRICE_NAMES, lambda value: cents(value) is not None, within="price")
    name = named(objects, NAME_NAMES, lambda value: isinstance(value, str) and capacity_in(value))
    model = named(objects, MODEL_NAMES, is_part_number)
    if not (price and name and model):
        return None
    stock, in_stock = stock_field(objects)
    return {
        "data_model_field": model,
        "data_name_field": name,
        "data_price_field": price,
        "data_brand_field": named(
            objects, BRAND_NAMES, lambda value: isinstance(value, str) and value.strip()
        ),
        "data_stock_field": stock,
        "data_in_stock_value": in_stock,
    }


def embedded_settings(page: str) -> dict[str, str] | None:
    """The data_ settings that read the products a page carries as JSON in a script: where the
    most priced products are, and which of their fields say what. None when it carries none."""
    best: tuple[int, dict[str, str]] | None = None
    for pattern, text in blobs(page):
        located = re.search(pattern, page, re.DOTALL)
        if located is None or located[1] != text:
            continue
        try:
            data = json.loads(js_string(text))
        except ValueError:
            continue
        for path, objects in collections([data]):
            fields = fields_of(objects)
            if fields is None:
                continue
            priced = sum(
                cents(item.get(fields["data_price_field"])) is not None for item in objects
            )
            if best is None or priced > best[0]:
                best = priced, {"data_pattern": pattern, "data_items": path, **fields}
    return best[1] if best else None


def path_pattern(path: str, listed: list[str]) -> str:
    """What the store's product pages have in common in their paths, going by this one and the
    paths its sitemap lists: a first part others share ("^/products/"), an ending to the first
    part others share ("-p/"), or, for a page at the top of the store, being at the top while
    other pages lie deeper ("^/[^/]+/?$"). "" when nothing is shared."""
    parts = [part for part in path.split("/") if part]
    others = [other for other in listed if other.rstrip("/") != path.rstrip("/")]
    if len(parts) < 2:
        deeper = any(other.strip("/").count("/") for other in others)
        return "^/[^/]+/?$" if parts and deeper else ""
    if any(other.startswith(f"/{parts[0]}/") for other in others):
        return f"^/{literal(parts[0])}/"
    ending = re.search(r"-[A-Za-z]{1,3}$", parts[0])
    if ending and any(f"{ending[0]}/" in other for other in others):
        return f"{literal(ending[0])}/"
    return ""


def price_markup(page: str) -> str:
    """How a page that is one product gives its price, in words."""
    tagged = re.search(r"itemprop=['\"]price['\"]", page)
    return "in schema.org tags in its markup" if tagged else "as a JSON-LD Product"


def pages(count: int) -> str:
    return f"{count} page{'' if count == 1 else 's'}"


# A sitemap is looked for in this many places before giving up on finding the page in one.
SITEMAPS_TRIED = 2


@dataclass(frozen=True)
class Listed:
    """What looking for a page in its store's sitemap found: the settings that read the
    sitemap (its path, when it is not the one a run would find for itself, and what its
    product pages' paths share); why, in sentences; how much there is to the store; and how
    many requests a run of it would make."""

    settings: dict[str, str]
    evidence: list[str]
    summary: list[Fact]
    requests: int | None


def in_sitemap(http: Pages, store: Store, path: str) -> Listed:
    """Where the store's sitemap lists this page. A sitemap index is not followed: reading
    every sitemap it names is what a wrong setting costs, so it is not done to find the right
    one."""
    named = http.sitemaps(store.base_url)
    default = f"{store.base_url}/sitemap.xml"
    for sitemap in list(dict.fromkeys([default, *named]))[:SITEMAPS_TRIED]:
        try:
            text = http.get(sitemap, min_delay=store.min_delay).text
        except SourceUnavailable:
            continue
        urls = [] if "<sitemapindex" in text else locations(text)
        listed = [urlsplit(url).path for url in urls if same_site(url, store.base_url)]
        if path.rstrip("/") not in {other.rstrip("/") for other in listed}:
            continue
        where = urlsplit(sitemap).path
        pattern = path_pattern(path, listed)
        # Counted as a run with these settings would find them: by the reader's own reading.
        suggested = SitemapSettings.of({**NOTHING_SET, "product_path_pattern": pattern})
        products = product_paths(urls, store.base_url, suggested)
        fetched = worth_fetching(products)
        changed = max(re.findall(r"<lastmod>\s*([^<\s]+)", text), default="")
        listing = f"The page is in the store's sitemap, {where}, which lists {pages(len(listed))}."
        shared = (
            f"{len(products)} of them match the product path pattern {pattern}."
            if pattern
            else "No product path pattern could be worked out from this page's address:"
            " every page the sitemap lists would be read."
        )
        return Listed(
            # The path is left blank when a run would read this sitemap, and only it, anyway.
            {
                "sitemap_path": "" if (named or [default]) == [sitemap] else where,
                "product_path_pattern": pattern,
            },
            [listing, shared],
            [
                Fact("Pages in the sitemap", f"{len(listed):,}"),
                Fact("Product pages", f"{len(products):,}"),
                # Without those named as accessories or memory, or, in a store whose product
                # pages mostly name a capacity, those that name none.
                Fact("Pages a run would fetch", f"{len(fetched):,}"),
                *([Fact("Sitemap last changed", changed[:10])] if changed else []),
            ],
            # Each page, and the sitemap itself.
            len(fetched) + 1,
        )
    missing = (
        "The page was not found in the store's sitemap, so a run would not read it: set the"
        " Sitemap path to the sitemap that lists it."
    )
    return Listed({}, [missing], [], None)


def json_ld_says(page: str) -> str:
    """What the page's JSON-LD has to do with there being no price, in words."""
    blocks = JSON_LD.findall(page)
    if not blocks:
        return "and it has no JSON-LD"
    if json_ld_product(page):
        return "and its JSON-LD describes a product without a price"
    kinds: list[str] = []
    for block in blocks:
        try:
            things = list(things_in(json.loads(block)))
        except ValueError:
            continue
        kinds += [str(thing.get("@type", "")).rsplit("/", 1)[-1] for thing in things]
    named = ", ".join(dict.fromkeys(kind for kind in kinds if kind))
    return f"and its JSON-LD describes no product (it describes: {named or 'nothing'})"


class Sitemap:
    description = described(
        "Sitemap + product page",
        SitemapSettings,
        groups=(
            Group(
                "data",
                "Pages that list several products",
                "For a store whose page covers a whole family of drives and carries them as"
                " JSON inside a script. Left blank, each page is one product, read from its"
                " own price markup.",
            ),
        ),
    )

    def settings(self, saved: Mapping[str, Any]) -> SitemapSettings:
        return SitemapSettings.of(saved)

    def offers(self, site: Site[SitemapSettings]) -> Iterator[ScrapedOffer]:
        return self._read(self._listed(site, tell_nobody), site, tell_nobody)

    def sample(self, site: Site[SitemapSettings], tell: Tell) -> Iterator[ScrapedOffer]:
        """The first few product pages its sitemap lists."""
        return self._read(self._listed(site, tell)[:SAMPLE_PAGES], site, tell)

    def page_offers(
        self, url: str, site: Site[SitemapSettings], tell: Tell
    ) -> Iterator[ScrapedOffer]:
        return self._read([url], site, tell)

    def _read(
        self, urls: list[str], site: Site[SitemapSettings], tell: Tell
    ) -> Iterator[ScrapedOffer]:
        """The offers on these pages, each page's as it is fetched; tell is told of a page that
        could not be fetched, or that gave no offer and why."""
        http, store, settings = site.http, site.store, site.settings
        for url, page in each_fetched(
            store.key, urls, lambda url: http.get(url, min_delay=store.min_delay).text, tell
        ):
            offers = offers_from_page(page, url, store, settings)
            if not offers:
                tell(f"{url}: {why_no_offers(page, settings)}")
            yield from offers

    def _listed(self, site: Site[SitemapSettings], tell: Tell) -> list[str]:
        """The product pages to read, from the store's sitemap."""
        store, settings = site.store, site.settings
        listed = page_urls(site.http, store, settings.sitemap_path)
        paths = worth_fetching(product_paths(listed, store.base_url, settings))
        log.info("sitemap_read", extra={"source": store.key, "pages": len(paths)})
        tell(
            f"The sitemap lists {len(listed)} page{'' if len(listed) == 1 else 's'};"
            f" {len(paths)} are product pages to read."
        )
        return [f"{store.base_url}{path}" for path in paths]

    def recheck(
        self, listings: Sequence[ListingSummary], site: Site[SitemapSettings]
    ) -> Iterator[Rechecked]:
        """Each on its product page; the models of a family that share one share its fetch."""

        def fetch(path: str) -> str | None:
            response = site.http.get_if_present(
                f"{site.store.base_url}{path}", min_delay=site.store.min_delay
            )
            return response.text if response is not None else None

        return rechecked(
            listings,
            lambda url: product_path(url, site.store.base_url, site.settings),
            fetch,
            lambda listing, page: recheck_offer(listing, page, site.store, site.settings),
        )

    def inspect(self, url: str, page: str, site: Site[None]) -> Inspection:
        """A page that gives its own price, or carries its products as data in a script, is a
        sitemap store's: each is a way of reading it. The store's sitemap is then looked in for
        the page, for the sitemap path and what its product pages' paths share."""
        notes: list[str] = []
        readings: list[Reading] = []

        def tried(settings: dict[str, str], evidence: str) -> str:
            """Keeps the reading these settings make; why they read no drive, when they do not."""
            read = SitemapSettings.of(settings)
            offers = offers_from_page(page, url, site.store, read)
            if not offers:
                return why_no_offers(page, read)
            readings.append(Reading(settings, [evidence], offers))
            return ""

        unpriced = tried(dict(NOTHING_SET), f"The page gives its price {price_markup(page)}.")
        if unpriced:
            notes.append(
                f"No price was found in the page's markup, {json_ld_says(page)}."
                if unpriced.startswith("no price")
                else f"The page's own markup gives no drive: {unpriced}."
            )
        data = embedded_settings(page)
        if data is None:
            notes.append("No product data was found in the page's scripts.")
        else:
            undriven = tried(
                {**NOTHING_SET, **data},
                "The page carries its products as data in one of its scripts.",
            )
            if undriven:
                notes.append(f"The data in the page's scripts gives no drive: {undriven}.")
        if readings:
            try:
                listed = in_sitemap(site.http, site.store, urlsplit(url).path)
            except OutOfTime as error:
                # The page was read; only where it sits among the store's pages was not.
                unfound = (
                    f"The store's sitemap was not found before time ran out ({error}), so its"
                    " sitemap path and product path pattern are not worked out."
                )
                listed = Listed({}, [unfound], [], None)
            readings = [
                replace(
                    reading,
                    settings={**reading.settings, **listed.settings},
                    evidence=[*reading.evidence, *listed.evidence],
                    summary=listed.summary,
                    requests=listed.requests,
                )
                for reading in readings
            ]
        return Inspection(readings, notes)
