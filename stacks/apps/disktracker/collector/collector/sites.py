"""Opening a source for reading: the reader for its kind, and the site that reader is given
(how its pages are fetched, its store, and its settings as the reader reads them)."""

import re
from collections.abc import Callable, Mapping
from typing import Any

from listing_facts.readers import ConditionRules

from collector.clock import Clock
from collector.errors import SourceUnavailable
from collector.models import Store
from collector.pacer import Pacer
from collector.polite import Fetcher, PoliteHttp
from collector.ports import Reader, Site


class Sites:
    def __init__(
        self,
        readers: Mapping[str, Reader[Any]],
        transports: Mapping[str, Fetcher],
        pacer: Pacer,
        clock: Clock,
        min_delay: float,
    ) -> None:
        """readers: the reader for each kind of source. transports: what a source's pages are
        fetched with, by its transport, each run or preview fetching them politely afresh
        (PoliteHttp), so that what it learns of robots.txt lasts only that long. pacer: what
        spaces requests to a store, however they are fetched. min_delay: the least time between
        two requests to a store."""
        self.readers, self.transports, self.min_delay = readers, transports, min_delay
        self.pacer, self.clock = pacer, clock

    def open(
        self,
        *,
        key: str,
        kind: str,
        base_url: str,
        transport: str,
        settings: Mapping[str, Any],
        conditions: ConditionRules,
        obey_robots: bool = True,
    ) -> tuple[Reader[Any], Site[Any]]:
        """The reader for a source and the site it is to read, at the start of a run or a
        preview. A source told not to obey robots.txt (only one the store permits) reads past
        it. A source that cannot be read as configured is unavailable, with the reason."""
        reader = self.readers.get(kind)
        if reader is None:
            raise SourceUnavailable(f"settings: a {kind} source is not collected")
        fetch = self._transport(transport)
        try:
            read = reader.settings(settings)
        except KeyError as error:
            raise SourceUnavailable(f"settings: missing {error.args[0]}") from error
        except (TypeError, ValueError, re.error) as error:
            raise SourceUnavailable(f"settings: {error}") from error
        http = fetch(None if obey_robots else key)
        return reader, Site(http, self._store(key, base_url, conditions), read)

    def visit(
        self, *, key: str, base_url: str, transport: str, conditions: ConditionRules
    ) -> Site[None]:
        """A store as it is before it has settings, for inspecting it: how its pages are
        fetched, obeying robots.txt."""
        http = self._transport(transport)(None)
        return Site(http, self._store(key, base_url, conditions), None)

    def _transport(self, transport: str) -> Callable[[str | None], PoliteHttp]:
        """How a source's pages are fetched for one run or preview, given the source when the
        store has permitted it to read past robots.txt, else None."""
        if transport not in self.transports:
            raise SourceUnavailable(f"settings: pages cannot be fetched by {transport}")
        fetcher = self.transports[transport]
        return lambda permitted: PoliteHttp(fetcher, self.pacer, self.clock, permitted=permitted)

    def _store(self, key: str, base_url: str, conditions: ConditionRules) -> Store:
        return Store(key, base_url.rstrip("/"), self.min_delay, conditions)
