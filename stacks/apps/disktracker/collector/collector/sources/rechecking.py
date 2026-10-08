"""Checking known offers again, for the readers: each offer on the page (or API answer) its
URL leads to, with a page several offers share fetched once."""

from collections.abc import Callable, Iterator, Sequence

from collector.errors import SourceUnavailable
from collector.models import ScrapedOffer
from collector.ports import Rechecked
from disktracker_api.models import ListingSummary


def rechecked[K, P](
    listings: Sequence[ListingSummary],
    key_of: Callable[[str], K | None],
    fetch: Callable[[K], P],
    read: Callable[[ListingSummary, P], ScrapedOffer],
) -> Iterator[Rechecked]:
    """Each listing whose URL key_of knows for a product page of the store, read from what
    fetch gets for that key; one whose page cannot be fetched is given with why. Whatever
    several listings share a key for is fetched once, the failure to fetch it included."""
    fetched: dict[K, P | SourceUnavailable] = {}
    for listing in listings:
        key = key_of(listing.url or "")
        if key is None:
            continue
        if key not in fetched:
            try:
                fetched[key] = fetch(key)
            except SourceUnavailable as error:
                fetched[key] = error
        page = fetched[key]
        if isinstance(page, SourceUnavailable):
            yield Rechecked(listing, None, str(page))
        else:
            yield Rechecked(listing, read(listing, page))
