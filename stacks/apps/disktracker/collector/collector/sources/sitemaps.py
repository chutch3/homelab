"""Finding a store's pages from its sitemap, for the readers that start there."""

import html
import logging
import re
from collections.abc import Callable, Iterable, Iterator

from collector.errors import SourceUnavailable
from collector.models import Store
from collector.polite import Pages
from collector.ports import tell_nobody

log = logging.getLogger(__name__)
# A sample reads at most this many of a store's product pages to find one offer.
SAMPLE_PAGES = 5


def locations(sitemap: str) -> list[str]:
    return [html.unescape(loc).strip() for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap)]


def page_urls(http: Pages, store: Store, sitemap_path: str) -> list[str]:
    """Every page URL the store's sitemap lists: the sitemap at sitemap_path when one is set,
    else the sitemaps robots.txt names, else /sitemap.xml. A sitemap index is followed one
    level down, each sitemap it names read once however often it names it."""
    roots = (
        [f"{store.base_url}{sitemap_path}"]
        if sitemap_path
        else http.sitemaps(store.base_url) or [f"{store.base_url}/sitemap.xml"]
    )
    urls = []
    for root in roots:
        sitemap = http.get(root, min_delay=store.min_delay).text
        if "<sitemapindex" not in sitemap:
            urls += locations(sitemap)
            continue
        for nested in dict.fromkeys(locations(sitemap)):
            urls += locations(http.get(nested, min_delay=store.min_delay).text)
    return urls


def each_fetched[T](
    source: str,
    urls: Iterable[str],
    fetch: Callable[[str], T],
    tell: Callable[[str], None] = tell_nobody,
) -> Iterator[tuple[str, T]]:
    """Each URL with what was fetched from it; one that cannot be fetched is reported as
    page_failed, and told, and the rest carry on."""
    for url in urls:
        try:
            yield url, fetch(url)
        except SourceUnavailable as error:
            log.warning("page_failed", extra={"source": source, "url": url, "error": str(error)})
            tell(f"{url}: could not be fetched ({error})")
