"""Asking the collector to do something now, without waiting for its next poll: reading one
offer from a source, to preview it, and inspecting a link to a store not yet read."""

import json
import urllib.error
import urllib.request
from typing import Any

# A preview through a browser can take a minute a page.
TIMEOUT_SECONDS = 180


class CollectorUnavailable(Exception):
    """The collector could not be asked, or failed; the message says which, for the user."""


class CollectorClient:
    def __init__(self, url: str | None) -> None:
        """url: where the collector's API is; None when there is no collector to ask."""
        self.url = url.rstrip("/") if url else None

    def preview(self, source: dict[str, Any]) -> dict[str, Any]:
        """What the collector read from the source: an offer, none, or why it could not."""
        return self._ask("/preview", source)

    def inspect(self, link: dict[str, Any]) -> dict[str, Any]:
        """The sources the collector found would read the page a link leads to, each with the
        offer it read from it; none; or why the page could not be read."""
        return self._ask("/inspect", link)

    def _ask(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if self.url is None:
            raise CollectorUnavailable("No collector is configured, so sources cannot be tested.")
        request = urllib.request.Request(
            f"{self.url}{path}",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                answer: dict[str, Any] = json.load(response)
                return answer
        except urllib.error.HTTPError as error:
            detail = json.load(error).get("detail", error.reason)
            raise CollectorUnavailable(f"The collector failed to read it: {detail}") from error
        except (OSError, ValueError) as error:
            raise CollectorUnavailable(f"The collector could not be reached: {error}") from error
