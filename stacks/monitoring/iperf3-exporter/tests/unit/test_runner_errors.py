"""Unit test for the runner's generic-exception fallback."""

from unittest.mock import patch

import pytest

from iperf3_exporter.runner import IPerf3Runner


class TestIPerf3RunnerErrors:
    @pytest.fixture
    def subject(self):
        return IPerf3Runner()

    def test_run_test_returns_unexpected_error_on_generic_exception(self, subject):
        # subprocess is a system boundary the runner owns the call to; patch it to
        # force the generic-except path (matches the existing test_runner.py pattern).
        with patch("subprocess.run", side_effect=ValueError("weird")):
            result = subject.run_test("somehost")
        assert result.success is False
        assert "Unexpected error" in result.error
        assert "weird" in result.error
