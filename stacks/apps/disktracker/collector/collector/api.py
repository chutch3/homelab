"""The collector's API, for work that should not wait for the next poll: previewing a source,
and inspecting a link to a store not yet read.
It runs beside the collection loop, in the same process, on the internal network only."""

import json
import logging
from collections.abc import Iterator
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any

from collector.inspect import Inspector, NotAPage
from collector.preview import NotASource, Previewer

log = logging.getLogger(__name__)


class Handler(BaseHTTPRequestHandler):
    def __init__(self, previewer: Previewer, inspector: Inspector, *args: Any) -> None:
        self.asked = {"/preview": previewer.preview, "/inspect": inspector.inspect}
        super().__init__(*args)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._answer(200, {"status": "ok"})
        else:
            self._answer(404, {"detail": "not found"})

    def do_POST(self) -> None:
        answer = self.asked.get(self.path)
        if answer is None:
            self._answer(404, {"detail": "not found"})
            return
        try:
            asked = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self._answer(200, answer(asked))
        except (ValueError, NotASource, NotAPage) as error:
            self._answer(422, {"detail": str(error)})
        except Exception as error:
            log.exception("preview_crashed", extra={"error": repr(error)})
            self._answer(500, {"detail": repr(error)})

    def _answer(self, status: int, body: dict[str, Any]) -> None:
        content = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format: str, *args: Any) -> None:
        log.debug("api_request", extra={"request": format % args})


def serve(previewer: Previewer, inspector: Inspector, port: int | None) -> Iterator[None]:
    """Serve the API on port while the collector runs; without a port there is no API."""
    if port is None:
        yield
        return
    server = ThreadingHTTPServer(("0.0.0.0", port), partial(Handler, previewer, inspector))
    Thread(target=server.serve_forever, daemon=True).start()
    log.info("api_started", extra={"port": port})
    try:
        yield
    finally:
        server.shutdown()
        server.server_close()
