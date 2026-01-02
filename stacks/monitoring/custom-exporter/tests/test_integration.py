"""
Integration tests for iperf3_exporter

These tests verify the HTTP server endpoints and full workflow.
"""
import json
import pytest
from unittest.mock import patch, MagicMock
from http.server import HTTPServer
from urllib.request import urlopen
from urllib.error import HTTPError
import threading
import time

from iperf3_exporter.server import create_probe_handler
from iperf3_exporter.runner import IPerf3Runner
from iperf3_exporter.metrics import PrometheusMetricsFormatter


class TestProbeHandlerHTTPEndpoints:
    """Integration tests for ProbeHandler HTTP endpoints"""

    @pytest.fixture(scope="class")
    def http_server(self):
        """Fixture to start HTTP server for testing"""
        port = 19579  # Use different port for testing
        base_url = f"http://localhost:{port}"

        # Create dependencies
        runner = IPerf3Runner()
        formatter = PrometheusMetricsFormatter()

        # Create handler with injected dependencies
        handler_class = create_probe_handler(runner, formatter)

        # Start server in background thread
        server = HTTPServer(("localhost", port), handler_class)
        server_thread = threading.Thread(target=server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        # Give server time to start
        time.sleep(0.5)

        yield base_url

        # Cleanup
        server.shutdown()
        server_thread.join(timeout=5)

    def test_health_endpoint_returns_200_ok(self, http_server):
        """Test /health endpoint returns 200 OK status"""
        # Act
        response = urlopen(f"{http_server}/health")

        # Assert
        assert response.status == 200

    def test_health_endpoint_returns_ok_message(self, http_server):
        """Test /health endpoint returns OK message in body"""
        # Act
        response = urlopen(f"{http_server}/health")
        body = response.read()

        # Assert
        assert body == b"OK\n"

    def test_index_endpoint_returns_200_ok(self, http_server):
        """Test / endpoint returns 200 OK status"""
        # Act
        response = urlopen(f"{http_server}/")

        # Assert
        assert response.status == 200

    def test_index_endpoint_returns_html_content_type(self, http_server):
        """Test / endpoint returns HTML content type"""
        # Act
        response = urlopen(f"{http_server}/")

        # Assert
        assert response.headers.get("Content-Type") == "text/html"

    def test_index_endpoint_includes_exporter_title(self, http_server):
        """Test / endpoint includes exporter title in HTML body"""
        # Act
        response = urlopen(f"{http_server}/")
        body = response.read().decode()

        # Assert
        assert "iPerf3 Prometheus Exporter" in body

    def test_probe_endpoint_returns_400_when_target_missing(self, http_server):
        """Test /probe endpoint returns 400 Bad Request when target parameter is missing"""
        # Act & Assert
        with pytest.raises(HTTPError) as exc_info:
            urlopen(f"{http_server}/probe")

        assert exc_info.value.code == 400

    @patch('subprocess.run')
    def test_probe_endpoint_returns_200_for_successful_test(self, mock_run, http_server):
        """Test /probe endpoint returns 200 OK for successful iperf3 test"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {"bytes": 1000000, "seconds": 5.0, "retransmits": 10},
                "sum_received": {"bytes": 999000, "seconds": 5.0}
            }
        })
        mock_run.return_value = mock_result

        # Act
        response = urlopen(f"{http_server}/probe?target=192.168.1.1:5201")

        # Assert
        assert response.status == 200

    @patch('subprocess.run')
    def test_probe_endpoint_returns_prometheus_content_type(self, mock_run, http_server):
        """Test /probe endpoint returns Prometheus text format content type"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {"bytes": 1000, "seconds": 5.0, "retransmits": 0},
                "sum_received": {"bytes": 900, "seconds": 5.0}
            }
        })
        mock_run.return_value = mock_result

        # Act
        response = urlopen(f"{http_server}/probe?target=192.168.1.1")

        # Assert
        assert response.headers.get("Content-Type") == "text/plain; version=0.0.4"

    @patch('subprocess.run')
    def test_probe_endpoint_includes_up_metric_for_success(self, mock_run, http_server):
        """Test /probe endpoint includes iperf3_up=1 metric for successful test"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {"bytes": 1000000, "seconds": 5.0, "retransmits": 10},
                "sum_received": {"bytes": 999000, "seconds": 5.0}
            }
        })
        mock_run.return_value = mock_result

        # Act
        response = urlopen(f"{http_server}/probe?target=192.168.1.1:5201")
        body = response.read().decode()

        # Assert
        assert 'iperf3_up{target="192.168.1.1:5201",port="5201"} 1' in body

    @patch('subprocess.run')
    def test_probe_endpoint_includes_all_metrics_from_test_results(self, mock_run, http_server):
        """Test /probe endpoint includes all metrics from iperf3 test results"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {"bytes": 1000000, "seconds": 5.0, "retransmits": 10},
                "sum_received": {"bytes": 999000, "seconds": 5.0}
            }
        })
        mock_run.return_value = mock_result

        # Act
        response = urlopen(f"{http_server}/probe?target=192.168.1.1:5201")
        body = response.read().decode()

        # Assert
        assert 'iperf3_sent_bytes{target="192.168.1.1:5201",port="5201"} 1000000' in body
        assert 'iperf3_received_bytes{target="192.168.1.1:5201",port="5201"} 999000' in body

    @patch('subprocess.run')
    def test_probe_endpoint_passes_custom_period_to_iperf3(self, mock_run, http_server):
        """Test /probe endpoint passes custom period parameter to iperf3 command"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {"bytes": 1000, "seconds": 10.0, "retransmits": 0},
                "sum_received": {"bytes": 1000, "seconds": 10.0}
            }
        })
        mock_run.return_value = mock_result

        # Act
        urlopen(f"{http_server}/probe?target=192.168.1.1&period=10")

        # Assert
        call_args = mock_run.call_args[0][0]
        assert "-t" in call_args
        duration_index = call_args.index("-t") + 1
        assert call_args[duration_index] == "10"

    @patch('subprocess.run')
    def test_probe_endpoint_passes_custom_port_to_iperf3(self, mock_run, http_server):
        """Test /probe endpoint passes custom port parameter to iperf3 command"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "end": {
                "sum_sent": {"bytes": 1000, "seconds": 5.0, "retransmits": 0},
                "sum_received": {"bytes": 1000, "seconds": 5.0}
            }
        })
        mock_run.return_value = mock_result

        # Act
        urlopen(f"{http_server}/probe?target=192.168.1.1&port=9999")

        # Assert
        call_args = mock_run.call_args[0][0]
        assert "-p" in call_args
        port_index = call_args.index("-p") + 1
        assert call_args[port_index] == "9999"

    @patch('subprocess.run')
    def test_probe_endpoint_returns_up_metric_zero_for_failed_test(self, mock_run, http_server):
        """Test /probe endpoint returns iperf3_up=0 metric for failed iperf3 test"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Connection refused"
        mock_run.return_value = mock_result

        # Act
        response = urlopen(f"{http_server}/probe?target=192.168.1.1")
        body = response.read().decode()

        # Assert
        assert 'iperf3_up{target="192.168.1.1",port="5201"} 0' in body

    @patch('subprocess.run')
    def test_probe_endpoint_returns_zero_values_for_failed_test(self, mock_run, http_server):
        """Test /probe endpoint returns zero metric values for failed iperf3 test"""
        # Arrange
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Connection refused"
        mock_run.return_value = mock_result

        # Act
        response = urlopen(f"{http_server}/probe?target=192.168.1.1")
        body = response.read().decode()

        # Assert
        assert 'iperf3_sent_bytes{target="192.168.1.1",port="5201"} 0' in body

    def test_unknown_path_returns_404_not_found(self, http_server):
        """Test unknown path returns 404 Not Found status"""
        # Act & Assert
        with pytest.raises(HTTPError) as exc_info:
            urlopen(f"{http_server}/unknown")

        assert exc_info.value.code == 404
