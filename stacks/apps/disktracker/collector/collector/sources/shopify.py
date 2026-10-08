"""A Shopify store: its public products.json lists every variant of a collection's products
with structured tags (capacity:, condition:, formFactor:, interface:, brand:).

A SKU's base (up to its first "_") is taken for an MPN or part number when the store keys its
SKUs that way (most titles name their own SKU base), or when a title names it. ServerPartDeals'
SKUs are the MPN or OEM part number plus a condition or tray suffix, and it lists one drive many
times under one SKU base, which becomes a single listing; a store's own SKU codes are left out. A collection leaves out
sold-out products, so an offer that drops out of it is rechecked on its own product page. A
sold-out product is reported at whatever price the store shows (some show a placeholder);
disktracker records no price for a sold-out offer."""

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from itertools import count
from typing import Any
from urllib.parse import parse_qs, urlsplit

from listing_text.readers import (
    ConditionRules,
    Specifications,
    capacity_in,
    condition_in,
    form_factor_named,
    intended_use_named,
    interface_named,
    maker_named,
    media_type_named,
    mpn_from_title,
    recording_named,
    specifications,
)

from collector.errors import SourceUnavailable
from collector.models import FREE_SHIPPING, TITLE_LIMIT, ScrapedOffer, Store
from collector.polite import json_of, same_site
from collector.ports import Inspection, Reading, Rechecked, Site, Tell, tell_nobody
from collector.settings import described, setting, settings_from
from collector.sources.rechecking import rechecked
from disktracker_api.models import ListingSummary

PAGE_SIZE = 250
# What every Shopify storefront's pages load or set up.
SHOPIFY = re.compile(r"cdn\.shopify\.com|\bShopify\.(shop|theme)\b")


@dataclass(frozen=True)
class ShopifySettings:
    collections: tuple[str, ...] = setting(
        "Collections",
        type="list",
        required=True,
        placeholder="hard-drives, solid-state-drives",
        description="Comma-separated collection handles",
    )
    free_shipping: bool = setting("Every order ships free", type="flag")

    @classmethod
    def of(cls, saved: Mapping[str, Any]) -> "ShopifySettings":
        return settings_from(cls, saved)

    @property
    def shipping_cents(self) -> int | None:
        return FREE_SHIPPING if self.free_shipping else None


def _tag(tags: list[str], name: str) -> str | None:
    prefix = f"{name.lower()}:"
    return next(
        (tag[len(prefix) :].strip() for tag in tags if tag.lower().startswith(prefix)), None
    )


def condition_of(product: dict[str, Any], conditions: ConditionRules) -> str | None:
    """Read from the title and the condition tag together, by the rules' order."""
    tag = _tag(product.get("tags") or [], "condition")
    return condition_in(conditions, product.get("title"), tag)


def capacity_from_tags(tags: list[str]) -> int | None:
    """Whole decimal gigabytes: 18TB is 18000, 960GB is 960."""
    return capacity_in(_tag(tags, "capacity") or "")


def specifications_from(product: dict[str, Any]) -> Specifications | None:
    """What the store states about the drive, in disktracker's normalized values."""
    tags = product.get("tags") or []
    title = product.get("title") or ""
    return specifications(
        media_type_named((product.get("product_type") or "").split(" > ")[0]),
        form_factor_named(_tag(tags, "formFactor") or ""),
        interface_named(_tag(tags, "interface") or ""),
        recording_named(title),
        intended_use_named(title),
    )


def mpn_from_sku(sku: str | None) -> str | None:
    return sku.split("_", 1)[0] or None if sku else None


def product_key(url: str, base_url: str) -> tuple[str, str | None] | None:
    """The product handle (and variant) a store URL points at, however the URL is written:
    with or without www., directly under /products/ or through a collection."""
    parts = urlsplit(url)
    match = re.search(r"/products/([^/]+)", parts.path)
    if not same_site(url, base_url) or not match:
        return None
    variant = parse_qs(parts.query).get("variant")
    return match[1], variant[0] if variant else None


def part_number_skus(products: list[dict[str, Any]]) -> set[str]:
    """The SKU bases that are MPNs or part numbers rather than the store's own codes: all of
    them when at least half the products' titles name their own SKU base (the store keys its
    SKUs by part number), otherwise only those some title names."""

    def base_of(product: dict[str, Any]) -> str | None:
        return mpn_from_sku(product["variants"][0].get("sku"))

    def names(title: str, base: str) -> bool:
        return bool(re.search(rf"(?<![0-9A-Z]){re.escape(base.upper())}(?![0-9A-Z])", title))

    bases = {
        base
        for product in products
        for variant in product["variants"]
        if (base := mpn_from_sku(variant.get("sku")))
    }
    with_sku = [product for product in products if base_of(product)]
    self_named = [
        product for product in with_sku if names(product["title"].upper(), base_of(product) or "")
    ]
    if with_sku and len(self_named) * 2 >= len(with_sku):
        return bases
    titles = " ".join(product["title"] for product in products).upper()
    return {base for base in bases if names(titles, base)}


def one_listing_per_drive(
    products: list[dict[str, Any]], conditions: ConditionRules, named: set[str]
) -> list[dict[str, Any]]:
    """A store can list one drive many times (bare, per Dell/HP tray, per alternate part number)
    under one named SKU base; keep a single listing per SKU base and condition, preferring the
    bare drive, then the cheapest."""
    groups: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    for product in products:
        sku = mpn_from_sku(product["variants"][0].get("sku"))
        base = sku if sku in named else f"handle:{product['handle']}"
        groups.setdefault((base, condition_of(product, conditions)), []).append(product)

    def preference(product: dict[str, Any]) -> tuple[bool, Decimal]:
        variant = product["variants"][0]
        return ("_NOTRAY" not in (variant.get("sku") or ""), Decimal(variant["price"]))

    return [min(group, key=preference) for group in groups.values()]


def parse_products(
    products: list[dict[str, Any]], store: Store, settings: ShopifySettings
) -> list[ScrapedOffer]:
    named = part_number_skus(products)

    def sku_mpn(sku: str | None) -> str | None:
        base = mpn_from_sku(sku)
        return base if base in named else None

    maker_mpns = {
        sku_mpn(product["variants"][0].get("sku")): mpn_from_title(product["title"])
        for product in products
        if mpn_from_title(product["title"])
    }
    listed = one_listing_per_drive(products, store.conditions, named)
    offers = []
    for product in listed:
        tags = product.get("tags") or []
        for variant in product["variants"]:
            base = sku_mpn(variant.get("sku"))
            maker = mpn_from_title(product["title"]) or (maker_mpns.get(base) if base else None)
            single = variant["title"] == "Default Title"
            url = f"{store.base_url}/products/{product['handle']}"
            title = product["title"] if single else f"{product['title']} ({variant['title']})"
            offers.append(
                ScrapedOffer(
                    source=store.key,
                    url=url if single else f"{url}?variant={variant['id']}",
                    title=title[:TITLE_LIMIT],
                    mpn=maker or base,
                    aliases=(base,) if maker and base and base != maker else (),
                    condition=condition_of(product, store.conditions),
                    brand=maker_named(product["title"]) or maker_named(_tag(tags, "brand") or ""),
                    capacity_gb=capacity_from_tags(tags),
                    item_price_cents=int(Decimal(variant["price"]) * 100),
                    in_stock=bool(variant["available"]),
                    shipping_cents=settings.shipping_cents,
                    specifications=specifications_from(product),
                )
            )
    return offers


def recheck_offer(
    listing: ListingSummary, page: dict[str, Any] | None, store: Store, settings: ShopifySettings
) -> ScrapedOffer:
    """A known offer as its product page shows it now (None when the page is gone)."""
    wanted = parse_qs(urlsplit(listing.url or "").query).get("variant")
    variants = (page or {}).get("variants", [])
    variant = next((v for v in variants if not wanted or str(v["id"]) == wanted[0]), None)
    return ScrapedOffer.recheck(
        listing,
        source=store.key,
        item_price_cents=int(variant["price"]) if variant else None,
        in_stock=bool(variant and variant["available"]),
        shipping_cents=settings.shipping_cents,
    )


class Shopify:
    description = described("Shopify", ShopifySettings)

    def settings(self, saved: Mapping[str, Any]) -> ShopifySettings:
        return ShopifySettings.of(saved)

    def offers(self, site: Site[ShopifySettings]) -> list[ScrapedOffer]:
        return self._read(site, site.settings.collections, every_page=True)

    def sample(self, site: Site[ShopifySettings], tell: Tell) -> list[ScrapedOffer]:
        """One page of the first collection."""
        return self._read(site, site.settings.collections[:1], every_page=False)

    def _read(
        self, site: Site[ShopifySettings], collections: tuple[str, ...], every_page: bool
    ) -> list[ScrapedOffer]:
        products: dict[int, dict[str, Any]] = {}
        for collection in collections:
            for page in count(1):
                batch = json_of(
                    site.http.get(
                        f"{site.store.base_url}/collections/{collection}/products.json",
                        params={"limit": PAGE_SIZE, "page": page},
                        min_delay=site.store.min_delay,
                    )
                )["products"]
                if not batch:
                    break
                # A product can be listed in several collections; it is one listing.
                products.update((product["id"], product) for product in batch)
                if not every_page:
                    break
        return parse_products(list(products.values()), site.store, site.settings)

    def recheck(
        self, listings: Sequence[ListingSummary], site: Site[ShopifySettings]
    ) -> Iterator[Rechecked]:
        """Each on its product's own page; the variants of one product share it."""

        def handle(url: str) -> str | None:
            key = product_key(url, site.store.base_url)
            return key[0] if key else None

        def fetch(product: str) -> dict[str, Any] | None:
            response = site.http.get_if_present(
                f"{site.store.base_url}/products/{product}.js", min_delay=site.store.min_delay
            )
            return json_of(response) if response is not None else None

        return rechecked(
            listings,
            handle,
            fetch,
            lambda listing, page: recheck_offer(listing, page, site.store, site.settings),
        )

    def inspect(self, url: str, page: str, site: Site[None]) -> Inspection:
        """A page that loads from Shopify is a Shopify store's. It is read as a run would read
        it: from the collection the link names, or, when it names none, the store's whole
        catalogue, the collection every Shopify store has as "all"."""
        if not SHOPIFY.search(page):
            return Inspection(
                [], ["The page loads nothing from Shopify, so the store is not one of its."]
            )
        path = urlsplit(url).path
        named = re.search(r"/collections/([^/]+)/products/", path)
        collection = named[1] if named else "all"
        settings = {"collections": [collection], "free_shipping": False}
        try:
            offers = self.sample(Site(site.http, site.store, self.settings(settings)), tell_nobody)
        except SourceUnavailable as error:
            return Inspection(
                [],
                [
                    f"It is a Shopify store, but its collection {collection} could not be read: {error}"
                ],
            )
        if not offers:
            return Inspection(
                [], [f"It is a Shopify store, but its collection {collection} lists no drive."]
            )
        evidence = [
            "The page is a Shopify store's.",
            f"The link names the collection {collection}; add any others that hold drives."
            if named
            else "The link names no collection, so all, the store's whole catalogue, is"
            " suggested: narrow it to the collections that hold drives.",
        ]

        def handle(address: str) -> str | None:
            key = product_key(address, site.store.base_url)
            return key[0] if key else None

        linked = [offer for offer in offers if handle(offer.url) == handle(url)]
        if not linked:
            evidence.append(
                f"The linked product is not among the first {PAGE_SIZE} the collection lists; the"
                " first offer read is shown instead."
            )
        others = [offer for offer in offers if offer not in linked]
        return Inspection([Reading(settings, evidence, [*linked, *others], bool(linked))], [])
