from __future__ import annotations

import pytest


def pytest_collection_finish(session: pytest.Session) -> None:
    """Disable coverage fail-under when only integration tests are collected (no unit tests)."""
    has_unit = any("tests/unit" in str(item.fspath) for item in session.items)
    if not has_unit:
        # Find the pytest-cov plugin and clear its fail-under threshold
        for name, plugin in session.config.pluginmanager.list_name_plugin():
            if hasattr(plugin, "options") and hasattr(plugin.options, "cov_fail_under"):
                plugin.options.cov_fail_under = None
                break
