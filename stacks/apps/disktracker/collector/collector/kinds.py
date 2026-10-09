"""The kinds of source the collector reads, as their readers describe them, for disktracker:
its backend checks a store's settings against these and its Admin form is drawn from them.
Run as a module, it prints them as JSON, which scripts/generate-source-kinds.sh keeps in the
backend."""

import json
from dataclasses import asdict
from typing import Any

from collector.container import Container
from collector.ports import ReadsOnePage


def described() -> dict[str, Any]:
    """Each kind's description, as plain data."""
    readers = Container().readers()
    kinds: dict[str, Any] = json.loads(
        json.dumps(
            {
                kind: {
                    **asdict(reader.description),
                    # One of its pages can be read alone to test it.
                    "page_test": isinstance(reader, ReadsOnePage),
                }
                for kind, reader in readers.items()
            }
        )
    )
    return kinds


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(described(), indent=2, sort_keys=True))
