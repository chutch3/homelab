"""A SAP Commerce (Hybris) store: its sitemap lists every product page with its SKU, and the
store's own pages read price and stock from its public OCC API, one SKU at a time. Western
Digital is one, selling WD, HGST and Ultrastar drives new and "Certified Refurbished".

The sitemap is the one at sitemap_path, or the ones robots.txt names, or /sitemap.xml; only its
pages whose path matches product_path_pattern (every page when it is blank) are read. Western
Digital's robots.txt names an index of every locale's sitemaps, so it is set to its products
sitemap. Requests are spaced by
COLLECTOR_MIN_DELAY_SECONDS even when the site asks for no crawl delay.

Drives are matched across stores by model number. A product's SKU is its model number, or a
part number (0F38352) when the API also gives a model number (WUH721818AL5201), which is then
sent as an alias. A page whose path says "recertified" is a recertified product, whose SKU is the new
one's with recertified_sku_prefix in front and which the API gives no model number: it goes by
that SKU without the prefix, which is the model number of a retail drive, and the part number,
which the new drive taught, of a data-center drive. New products are therefore read first.

Products listed without a price (placeholders for a product family, drives no longer sold)
are not offers. Shipping is not in the API, so it is recorded as unknown."""

import logging
import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from functools import cached_property
from typing import Any
from urllib.parse import parse_qs, urlsplit

from listing_text.readers import (
    capacity_in,
    condition_in,
    intended_use_named,
    interface_named,
    maker_named,
    recording_named,
    specifications,
)

from collector.models import TITLE_LIMIT, ScrapedOffer, Store
from collector.polite import json_of, same_site
from collector.ports import Inspection, Rechecked, Site, Tell
from collector.settings import described, setting, settings_from
from collector.sources.rechecking import rechecked
from collector.sources.sitemaps import SAMPLE_PAGES, each_fetched, page_urls
from disktracker_api.models import ListingSummary

log = logging.getLogger(__name__)
MEDIA_TYPES = {"cc_hdd": "hdd", "cc_ssd": "ssd"}
IN_STOCK = ("inStock", "lowStock")


@dataclass(frozen=True)
class SapCommerceSettings:
    api_url: str = setting(
        "API URL",
        required=True,
        placeholder="https://api.example.com/occ/v2",
        pattern=r"^https?://[^\s/]+\S*$",
        pattern_message="Enter the API's address, starting http:// or https://.",
    )
    site: str = setting("Site", required=True, placeholder="us")
    sitemap_path: str = setting(
        "Sitemap path",
        placeholder="/sitemap.xml",
        description="Blank: the sitemap robots.txt names, or /sitemap.xml",
        pattern=r"^(/\S*)?$",
        pattern_message="Start it with /.",
    )
    product_path_pattern: str = setting(
        "Product path pattern",
        placeholder="^/products/",
        description="A regular expression the product pages to read match; blank reads every page",
        regex=True,
    )
    # Put before a recertified product's SKU; dropped to find its model or part number.
    recertified_sku_prefix: str = setting(
        "Recertified SKU prefix",
        placeholder="R",
        description="Put before a recertified product's SKU",
    )

    def __post_init__(self) -> None:
        # A pattern that is no regular expression is refused when the settings are read.
        _ = self.product_path

    @classmethod
    def of(cls, saved: Mapping[str, Any]) -> "SapCommerceSettings":
        return settings_from(cls, saved)

    @property
    def products_url(self) -> str:
        return f"{self.api_url.rstrip('/')}/{self.site}/products"

    @cached_property
    def product_path(self) -> re.Pattern[str]:
        return re.compile(self.product_path_pattern)

    @staticmethod
    def recertified(url: str) -> bool:
        """Whether a product page is for a recertified product, as its path says."""
        return "recertified" in urlsplit(url).path.lower()


def sku_in(url: str) -> str | None:
    skus = parse_qs(urlsplit(url).query).get("sku")
    return skus[0] if skus else None


def product_pages(urls: list[str], settings: SapCommerceSettings) -> list[str]:
    """The sitemap's product pages to read, new products before recertified ones."""
    pages = [
        url for url in urls if settings.product_path.search(urlsplit(url).path) and sku_in(url)
    ]
    return sorted(pages, key=settings.recertified)


def sku_of(url: str, base_url: str) -> str | None:
    """The SKU of one of this store's product pages, however the host is written."""
    if not same_site(url, base_url) or not urlsplit(url).path.startswith("/products/"):
        return None
    return sku_in(url)


def features(product: dict[str, Any]) -> dict[str, str]:
    return {
        feature["codeShort"]: feature["featureValues"][0]["value"]
        for group in product.get("classifications") or []
        for feature in group["features"]
        if feature.get("featureValues")
    }


def capacity_of(product: dict[str, Any]) -> int | None:
    capacity = next(
        (
            category["name"]
            for category in product.get("categories") or []
            if "/vc-capacity/" in category.get("codePath", "")
        ),
        product.get("name") or "",
    )
    return capacity_in(capacity)


def price_cents(product: dict[str, Any]) -> int | None:
    price = product.get("price")
    return int(Decimal(str(price["value"])) * 100) if price else None


def in_stock(product: dict[str, Any]) -> bool:
    """On sale now: a store can list products it does not sell, with no price, as in stock."""
    status = (product.get("stock") or {}).get("stockLevelStatus")
    return status in IN_STOCK and price_cents(product) is not None


def offer_from_product(
    product: dict[str, Any], url: str, store: Store, settings: SapCommerceSettings
) -> ScrapedOffer | None:
    """The offer the API describes, or None when the store does not sell it (no price) or it
    names no capacity."""
    capacity = capacity_of(product)
    if capacity is None or price_cents(product) is None:
        return None
    recertified = settings.recertified(url)
    prefix = settings.recertified_sku_prefix if recertified else ""
    found = features(product)
    part = product["code"].removeprefix(prefix)
    model = found.get("modelNumber", product["code"]).removeprefix(prefix)
    name = product.get("name") or model
    media = next((MEDIA_TYPES[g["code"]] for g in product.get("classifications") or []
                  if g["code"] in MEDIA_TYPES), None)  # fmt: skip
    return ScrapedOffer(
        source=store.key,
        url=url,
        title=name[:TITLE_LIMIT],
        mpn=model,
        aliases=(part,) if part != model else (),
        condition=condition_in(store.conditions, name)
        or ("manufacturer_recertified" if recertified else "new"),
        brand=maker_named((product.get("brand") or {}).get("name") or ""),
        capacity_gb=capacity,
        item_price_cents=price_cents(product),
        in_stock=in_stock(product),
        specifications=specifications(
            media,
            None,
            interface_named(found.get("interface", "")),
            recording_named(name),
            intended_use_named(name),
        ),
    )


def recheck_offer(
    listing: ListingSummary, product: dict[str, Any] | None, store: Store
) -> ScrapedOffer:
    """A known offer as the API shows it now (None when the SKU is gone)."""
    return ScrapedOffer.recheck(
        listing,
        source=store.key,
        item_price_cents=price_cents(product) if product else None,
        in_stock=bool(product and in_stock(product)),
        shipping_cents=None,
    )


class SapCommerce:
    description = described("SAP Commerce", SapCommerceSettings)

    def settings(self, saved: Mapping[str, Any]) -> SapCommerceSettings:
        return SapCommerceSettings.of(saved)

    def offers(self, site: Site[SapCommerceSettings]) -> Iterator[ScrapedOffer]:
        return self._read(site, self._listed(site))

    def sample(self, site: Site[SapCommerceSettings], tell: Tell) -> Iterator[ScrapedOffer]:
        """The first few products its sitemap lists."""
        return self._read(site, self._listed(site)[:SAMPLE_PAGES])

    def _listed(self, site: Site[SapCommerceSettings]) -> list[str]:
        """The product pages its sitemap lists."""
        listed = page_urls(site.http, site.store, site.settings.sitemap_path)
        pages = product_pages(listed, site.settings)
        log.info("sitemap_read", extra={"source": site.store.key, "pages": len(pages)})
        return pages

    def _read(self, site: Site[SapCommerceSettings], pages: list[str]) -> Iterator[ScrapedOffer]:
        http, store, settings = site.http, site.store, site.settings
        # Each product is read from the API, by the SKU its page names.
        page_of = {f"{settings.products_url}/{sku_in(page)}": page for page in pages}
        for url, product in each_fetched(
            store.key,
            page_of,
            lambda url: json_of(http.get(url, {"fields": "FULL"}, store.min_delay)),
        ):
            offer = offer_from_product(product, page_of[url], store, settings)
            if offer is not None:
                yield offer

    def recheck(
        self, listings: Sequence[ListingSummary], site: Site[SapCommerceSettings]
    ) -> Iterator[Rechecked]:
        """Each from the API, by the SKU its page names."""

        def fetch(sku: str) -> dict[str, Any] | None:
            response = site.http.get_if_present(
                f"{site.settings.products_url}/{sku}", {"fields": "FULL"}, site.store.min_delay
            )
            return json_of(response) if response is not None else None

        return rechecked(
            listings,
            lambda url: sku_of(url, site.store.base_url),
            fetch,
            lambda listing, product: recheck_offer(listing, product, site.store),
        )

    def inspect(self, url: str, page: str, site: Site[None]) -> Inspection:
        """Not told from a page yet: its API's address and site are in no page."""
        return Inspection([], ["SAP Commerce stores are not recognised from a link yet."])
