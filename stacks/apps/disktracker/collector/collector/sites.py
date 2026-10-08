"""Opening a source for reading: the reader for its kind, and the site that reader is given
(how its pages are fetched, its store, and its settings as the reader reads them)."""

import re
from collections.abc import Mapping
from typing import Any

from listing_text.readers import ConditionRules

from collector.errors import SourceUnavailable
from collector.models import Store
from collector.polite import PoliteHttp
from collector.ports import Reader, Site


class Sites:
    def __init__(
        self,
        readers: Mapping[str, Reader[Any]],
        transports: Mapping[str, PoliteHttp],
        min_delay: float,
    ) -> None:
        """readers: the reader for each kind of source. transports: how pages are fetched, by
        a source's transport. min_delay: the least time between two requests to a store."""
        self.readers, self.transports, self.min_delay = readers, transports, min_delay

    def open(
        self,
        *,
        key: str,
        kind: str,
        base_url: str,
        transport: str,
        settings: Mapping[str, Any],
        conditions: ConditionRules,
    ) -> tuple[Reader[Any], Site[Any]]:
        """The reader for a source and the site it is to read, at the start of a run or a
        preview: what its transport knew of robots.txt is forgotten, so each reads it afresh.
        A source that cannot be read as configured is unavailable, with the reason."""
        reader = self.readers.get(kind)
        if reader is None:
            raise SourceUnavailable(f"settings: a {kind} source is not collected")
        if transport not in self.transports:
            raise SourceUnavailable(f"settings: pages cannot be fetched by {transport}")
        try:
            read = reader.settings(settings)
        except KeyError as error:
            raise SourceUnavailable(f"settings: missing {error.args[0]}") from error
        except (TypeError, ValueError, re.error) as error:
            raise SourceUnavailable(f"settings: {error}") from error
        site = self.visit(key=key, base_url=base_url, transport=transport, conditions=conditions)
        return reader, Site(site.http, site.store, read)

    def visit(
        self, *, key: str, base_url: str, transport: str, conditions: ConditionRules
    ) -> Site[None]:
        """A store as it is before it has settings, for inspecting it: how its pages are
        fetched, with what its transport knew of robots.txt forgotten."""
        if transport not in self.transports:
            raise SourceUnavailable(f"settings: pages cannot be fetched by {transport}")
        store = Store(key, base_url.rstrip("/"), self.min_delay, conditions)
        http = self.transports[transport]
        http.forget_rules()
        return Site(http, store, None)
