"""
Unit tests for iperf3_exporter.metrics module
"""
import pytest

from iperf3_exporter.metrics import PrometheusMetricsFormatter
from iperf3_exporter.runner import IPerf3Result


class TestPrometheusMetricsFormatter:
    """Test cases for PrometheusMetricsFormatter"""

    @pytest.fixture
    def subject(self):
        """Fixture providing the test subject"""
        return PrometheusMetricsFormatter()

    def test_format_sets_up_metric_to_one_for_successful_result(self, subject):
        """Test format sets iperf3_up metric to 1 for successful result"""
        # Arrange
        result = IPerf3Result(success=True, sent_bytes=1000, received_bytes=900)

        # Act
        metrics = subject.format(result, "192.168.1.1", 5201)

        # Assert
        assert 'iperf3_up{target="192.168.1.1",port="5201"} 1' in metrics

    def test_format_includes_all_metric_values_for_successful_result(self, subject):
        """Test format includes all metric values for successful result"""
        # Arrange
        result = IPerf3Result(
            success=True,
            sent_bytes=1000000,
            sent_seconds=5.5,
            received_bytes=999000,
            received_seconds=5.5,
            retransmits=10
        )

        # Act
        metrics = subject.format(result, "192.168.1.1", 5201)

        # Assert
        assert 'iperf3_sent_bytes{target="192.168.1.1",port="5201"} 1000000' in metrics
        assert 'iperf3_sent_seconds{target="192.168.1.1",port="5201"} 5.5' in metrics
        assert 'iperf3_received_bytes{target="192.168.1.1",port="5201"} 999000' in metrics
        assert 'iperf3_received_seconds{target="192.168.1.1",port="5201"} 5.5' in metrics
        assert 'iperf3_retransmits{target="192.168.1.1",port="5201"} 10' in metrics

    def test_format_includes_help_and_type_metadata_for_each_metric(self, subject):
        """Test format includes HELP and TYPE metadata for each metric"""
        # Arrange
        result = IPerf3Result(success=True, sent_bytes=1000, received_bytes=900)

        # Act
        metrics = subject.format(result, "192.168.1.1", 5201)

        # Assert
        assert '# HELP iperf3_up' in metrics
        assert '# TYPE iperf3_up gauge' in metrics
        assert '# HELP iperf3_sent_bytes' in metrics
        assert '# TYPE iperf3_sent_bytes gauge' in metrics

    def test_format_sets_up_metric_to_zero_for_failed_result(self, subject):
        """Test format sets iperf3_up metric to 0 for failed result"""
        # Arrange
        result = IPerf3Result(success=False, error="Connection refused")

        # Act
        metrics = subject.format(result, "192.168.1.1", 5201)

        # Assert
        assert 'iperf3_up{target="192.168.1.1",port="5201"} 0' in metrics

    def test_format_sets_all_metrics_to_zero_for_failed_result(self, subject):
        """Test format sets all metric values to zero for failed result"""
        # Arrange
        result = IPerf3Result(success=False, error="Connection refused")

        # Act
        metrics = subject.format(result, "192.168.1.1", 5201)

        # Assert
        assert 'iperf3_sent_bytes{target="192.168.1.1",port="5201"} 0' in metrics
        assert 'iperf3_sent_seconds{target="192.168.1.1",port="5201"} 0' in metrics
        assert 'iperf3_received_bytes{target="192.168.1.1",port="5201"} 0' in metrics
        assert 'iperf3_received_seconds{target="192.168.1.1",port="5201"} 0' in metrics
        assert 'iperf3_retransmits{target="192.168.1.1",port="5201"} 0' in metrics

    def test_format_includes_hostname_in_target_label(self, subject):
        """Test format includes hostname in target label when hostname is provided"""
        # Arrange
        result = IPerf3Result(success=True, sent_bytes=500000, received_bytes=499000)

        # Act
        metrics = subject.format(result, "server.example.com", 5201)

        # Assert
        assert 'target="server.example.com"' in metrics
        assert 'port="5201"' in metrics

    def test_format_includes_custom_port_in_port_label(self, subject):
        """Test format includes custom port in port label"""
        # Arrange
        result = IPerf3Result(success=True, sent_bytes=100000, received_bytes=99900)

        # Act
        metrics = subject.format(result, "192.168.1.1", 9999)

        # Assert
        assert 'port="9999"' in metrics

    def test_format_handles_zero_values_correctly(self, subject):
        """Test format handles zero metric values correctly"""
        # Arrange
        result = IPerf3Result(
            success=True,
            sent_bytes=0,
            sent_seconds=0.0,
            received_bytes=0,
            received_seconds=0.0,
            retransmits=0
        )

        # Act
        metrics = subject.format(result, "192.168.1.1", 5201)

        # Assert
        assert 'iperf3_up{target="192.168.1.1",port="5201"} 1' in metrics
        assert 'iperf3_sent_bytes{target="192.168.1.1",port="5201"} 0' in metrics

    def test_format_produces_valid_prometheus_text_format_structure(self, subject):
        """Test format produces valid Prometheus text format with correct structure"""
        # Arrange
        result = IPerf3Result(
            success=True,
            sent_bytes=1000,
            sent_seconds=1.0,
            received_bytes=900,
            received_seconds=1.0,
            retransmits=0
        )

        # Act
        metrics = subject.format(result, "test", 5201)

        # Assert
        lines = metrics.strip().split('\n')
        help_lines = [l for l in lines if l.startswith('# HELP')]
        type_lines = [l for l in lines if l.startswith('# TYPE')]
        value_lines = [l for l in lines if not l.startswith('#') and l.strip()]

        assert len(help_lines) == 6, "Should have HELP line for each of 6 metrics"
        assert len(type_lines) == 6, "Should have TYPE line for each of 6 metrics"
        assert len(value_lines) == 6, "Should have value line for each of 6 metrics"
