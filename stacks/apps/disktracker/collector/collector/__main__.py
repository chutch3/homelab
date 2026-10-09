"""Entry point: build the collector, then collect what is due once, or on every poll until stopped."""

import signal
import sys
import threading

from collector.container import Container
from collector.logger import configure


def main() -> None:
    container = Container()
    configure(container.config().log_level)
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    container.init_resources()
    try:
        status = container.schedule().run(stop)
    finally:
        container.shutdown_resources()
    sys.exit(status)


if __name__ == "__main__":
    main()
