import json
import logging
from collections.abc import Iterator

import pytest

from collector.logger import configure


@pytest.fixture(autouse=True)
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    yield
    root.handlers[:], root.level = handlers, level
    for name in ("httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.NOTSET)


def lines(output: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in output.strip().splitlines()]


def test_each_line_is_json_with_when_how_severe_where_and_what(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure("INFO")

    logging.getLogger("collector.collection").warning(
        "page_failed", extra={"url": "https://a.test"}
    )

    [line] = lines(capsys.readouterr().out)
    assert set(line) == {"ts", "level", "logger", "event", "url"}
    assert (line["level"], line["logger"], line["event"], line["url"]) == (
        "WARNING",
        "collector.collection",
        "page_failed",
        "https://a.test",
    )


def test_http_library_requests_show_only_at_debug(capsys: pytest.CaptureFixture[str]) -> None:
    configure("INFO")
    logging.getLogger("httpx").info("HTTP Request: GET https://a.test")
    logging.getLogger("collector").debug("offer_posted")
    assert capsys.readouterr().out == ""

    configure("DEBUG")
    logging.getLogger("httpx").info("HTTP Request: GET https://a.test")
    logging.getLogger("collector").debug("offer_posted")
    assert [line["event"] for line in lines(capsys.readouterr().out)] == [
        "HTTP Request: GET https://a.test",
        "offer_posted",
    ]
