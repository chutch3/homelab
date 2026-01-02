"""
Unit tests for iperf3_exporter.runner module
"""
import json
import subprocess
from unittest.mock import patch, MagicMock
import pytest

from iperf3_exporter.runner import IPerf3Runner, IPerf3Result


class TestIPerf3Runner:
    """Test cases for IPerf3Runner"""

    @pytest.fixture
    def subject(self):
        """Fixture providing the test subject"""
        return IPerf3Runner()

    @pytest.fixture
    def custom_subject(self):
        """Fixture providing a subject with custom configuration"""
        return IPerf3Runner(iperf3_path="/usr/bin/iperf3", timeout_offset=15)

    def test_init_sets_default_iperf3_path(self, subject):
        """Test runner initialization sets default iperf3 path"""
        assert subject.iperf3_path == "iperf3"

    def test_init_sets_default_timeout_offset(self, subject):
        """Test runner initialization sets default timeout offset"""
        assert subject.timeout_offset == 10

    def test_init_accepts_custom_iperf3_path(self, custom_subject):
        """Test runner initialization accepts custom iperf3 path"""
        assert custom_subject.iperf3_path == "/usr/bin/iperf3"

    def test_init_accepts_custom_timeout_offset(self, custom_subject):
        """Test runner initialization accepts custom timeout offset"""
        assert custom_subject.timeout_offset == 15

    @patch('subprocess.run')
    def test_run_test_returns_success_with_valid_output(self, mock_run, subject):
        """Test run_test returns successful result with valid iperf3 output"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {
                    "bytes": 1000000,
                    "seconds": 5.0,
                    "retransmits": 10
                },
                "sum_received": {
                    "bytes": 999000,
                    "seconds": 5.0
                }
            }
        })
        mock_run.return_value = mock_result

        # Act
        result = subject.run_test("192.168.1.1", 5201, 5)

        # Assert
        assert result.success is True
        assert result.sent_bytes == 1000000
        assert result.sent_seconds == 5.0
        assert result.received_bytes == 999000
        assert result.received_seconds == 5.0
        assert result.retransmits == 10
        assert result.error is None

    @patch('subprocess.run')
    def test_run_test_calls_iperf3_with_correct_arguments(self, mock_run, subject):
        """Test run_test calls iperf3 subprocess with correct arguments"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({"end": {"sum_sent": {}, "sum_received": {}}})
        mock_run.return_value = mock_result

        # Act
        subject.run_test("192.168.1.1", 5201, 5)

        # Assert
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args == ["iperf3", "-c", "192.168.1.1", "-p", "5201", "-t", "5", "-J"]

    @patch('subprocess.run')
    def test_run_test_returns_failure_on_nonzero_exit_code(self, mock_run, subject):
        """Test run_test returns failure result when iperf3 exits with non-zero code"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Connection refused"
        mock_run.return_value = mock_result

        # Act
        result = subject.run_test("192.168.1.1", 5201, 5)

        # Assert
        assert result.success is False
        assert "exited with code 1" in result.error
        assert "Connection refused" in result.error

    @patch('subprocess.run')
    def test_run_test_returns_failure_on_timeout(self, mock_run, subject):
        """Test run_test returns failure result when subprocess times out"""
        # Arrange
        mock_run.side_effect = subprocess.TimeoutExpired("iperf3", 15)

        # Act
        result = subject.run_test("192.168.1.1", 5201, 5)

        # Assert
        assert result.success is False
        assert "timed out" in result.error
        assert "15 seconds" in result.error

    @patch('subprocess.run')
    def test_run_test_returns_failure_when_binary_not_found(self, mock_run, subject):
        """Test run_test returns failure result when iperf3 binary is not found"""
        # Arrange
        mock_run.side_effect = FileNotFoundError()

        # Act
        result = subject.run_test("192.168.1.1", 5201, 5)

        # Assert
        assert result.success is False
        assert "not found" in result.error
        assert "iperf3" in result.error

    @patch('subprocess.run')
    def test_run_test_returns_failure_on_invalid_json(self, mock_run, subject):
        """Test run_test returns failure result when iperf3 outputs invalid JSON"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "not valid json"
        mock_run.return_value = mock_result

        # Act
        result = subject.run_test("192.168.1.1", 5201, 5)

        # Assert
        assert result.success is False
        assert "Failed to parse" in result.error

    @patch('subprocess.run')
    def test_run_test_handles_missing_json_fields_gracefully(self, mock_run, subject):
        """Test run_test handles missing JSON fields by using zero values"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {},
                "sum_received": {}
            }
        })
        mock_run.return_value = mock_result

        # Act
        result = subject.run_test("192.168.1.1", 5201, 5)

        # Assert
        assert result.success is True
        assert result.sent_bytes == 0
        assert result.sent_seconds == 0.0
        assert result.received_bytes == 0
        assert result.received_seconds == 0.0
        assert result.retransmits == 0

    def test_parse_json_output_extracts_all_metrics_correctly(self, subject):
        """Test _parse_json_output correctly extracts all metrics from valid JSON"""
        # Arrange
        json_output = json.dumps({
            "end": {
                "sum_sent": {
                    "bytes": 5000000,
                    "seconds": 10.5,
                    "retransmits": 42
                },
                "sum_received": {
                    "bytes": 4998000,
                    "seconds": 10.5
                }
            }
        })

        # Act
        result = subject._parse_json_output(json_output)

        # Assert
        assert result.success is True
        assert result.sent_bytes == 5000000
        assert result.sent_seconds == 10.5
        assert result.received_bytes == 4998000
        assert result.received_seconds == 10.5
        assert result.retransmits == 42


class TestIPerf3Result:
    """Test cases for IPerf3Result dataclass"""

    def test_create_successful_result_sets_all_fields(self):
        """Test creating successful result sets all provided fields correctly"""
        # Act
        result = IPerf3Result(
            success=True,
            sent_bytes=1000,
            sent_seconds=5.0,
            received_bytes=900,
            received_seconds=5.0,
            retransmits=5
        )

        # Assert
        assert result.success is True
        assert result.sent_bytes == 1000
        assert result.sent_seconds == 5.0
        assert result.received_bytes == 900
        assert result.received_seconds == 5.0
        assert result.retransmits == 5
        assert result.error is None

    def test_create_failed_result_sets_error_message(self):
        """Test creating failed result sets error message correctly"""
        # Act
        result = IPerf3Result(
            success=False,
            error="Connection failed"
        )

        # Assert
        assert result.success is False
        assert result.error == "Connection failed"

    def test_create_failed_result_uses_default_zero_values(self):
        """Test creating failed result uses default zero values for metrics"""
        # Act
        result = IPerf3Result(
            success=False,
            error="Connection failed"
        )

        # Assert
        assert result.sent_bytes == 0
        assert result.sent_seconds == 0.0
        assert result.received_bytes == 0
        assert result.received_seconds == 0.0
        assert result.retransmits == 0
