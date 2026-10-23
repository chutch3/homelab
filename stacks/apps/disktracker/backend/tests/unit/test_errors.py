"""What can go wrong in a workflow is said apart from how it is answered over HTTP: a service
raising one needs neither the web framework nor how a store's settings are worded."""

import ast
from pathlib import Path

import disktracker.errors

ANSWERING = ("fastapi", "starlette", "disktracker.http_errors", "disktracker.collector")


def test_the_errors_a_workflow_raises_import_nothing_of_the_web_or_settings_presentation() -> None:
    tree = ast.parse(Path(disktracker.errors.__file__).read_text())
    imported = [
        name
        for node in ast.walk(tree)
        for name in (
            [alias.name for alias in node.names] if isinstance(node, ast.Import)
            else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
        )
    ]  # fmt: skip

    assert not [name for name in imported if name.startswith(ANSWERING)]
