#!/usr/bin/env python3
"""A stand-in for the Technitium DNS API, so the dns role can be tested without one.

Requests are counted to --count-file so a test can assert how many times a task tried.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer

REJECTED = {"status": "error", "errorMessage": "Invalid username or password for user: admin"}
ACCEPTED = {"status": "ok", "token": "stub-token"}
FLUSHED = {"status": "ok", "response": {}}


class Handler(BaseHTTPRequestHandler):
    args: argparse.Namespace
    counts: Counter[str]

    def _send(self, code: int, body: dict[str, object] | str) -> None:
        payload = (json.dumps(body) if isinstance(body, dict) else body).encode()
        self.send_response(code)
        self.send_header(
            "Content-Type", "application/json" if isinstance(body, dict) else "text/plain"
        )
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _route(self) -> None:
        path = self.path.split("?")[0]
        self.counts[path] += 1
        self._write_counts()
        if path == "/api/user/login":
            # A server still binding answers with no JSON body at all, which is
            # what the role's `until` waits on.
            if self.counts[path] <= self.args.refuse_first:
                self._send(503, "starting")
            elif self.args.reject_login:
                self._send(200, REJECTED)
            else:
                self._send(200, ACCEPTED)
        elif path == "/api/cache/flush":
            self._send(200, FLUSHED)
        else:
            self._send(404, {"status": "error", "errorMessage": f"no route {path}"})

    def _write_counts(self) -> None:
        with open(self.args.count_file, "w") as handle:
            json.dump(dict(self.counts), handle)

    do_GET = _route
    do_POST = _route

    def log_message(self, fmt: str, *fmt_args: object) -> None:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--count-file", required=True)
    parser.add_argument("--reject-login", action="store_true")
    parser.add_argument("--refuse-first", type=int, default=0)
    Handler.args = parser.parse_args()
    Handler.counts = Counter()
    with open(Handler.args.count_file, "w") as handle:
        json.dump({}, handle)
    HTTPServer(("127.0.0.1", Handler.args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
