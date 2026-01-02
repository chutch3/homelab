"""
Prometheus metrics formatting module

Converts iperf3 results to Prometheus text format.
"""
from typing import Dict
from .runner import IPerf3Result


class PrometheusMetricsFormatter:
    """Formats iperf3 results as Prometheus metrics"""

    @staticmethod
    def format(result: IPerf3Result, target: str, port: int) -> str:
        """
        Format iperf3 result as Prometheus metrics.

        Args:
            result: IPerf3Result from a test run
            target: Target host (for labels)
            port: Target port (for labels)

        Returns:
            Prometheus text format metrics
        """
        labels = f'target="{target}",port="{port}"'
        up_value = 1 if result.success else 0

        metrics = [
            "# HELP iperf3_up Was the last iperf3 probe successful",
            "# TYPE iperf3_up gauge",
            f"iperf3_up{{{labels}}} {up_value}",
            "",
            "# HELP iperf3_sent_bytes Total sent bytes",
            "# TYPE iperf3_sent_bytes gauge",
            f"iperf3_sent_bytes{{{labels}}} {result.sent_bytes}",
            "",
            "# HELP iperf3_sent_seconds Total seconds spent sending",
            "# TYPE iperf3_sent_seconds gauge",
            f"iperf3_sent_seconds{{{labels}}} {result.sent_seconds}",
            "",
            "# HELP iperf3_received_bytes Total received bytes",
            "# TYPE iperf3_received_bytes gauge",
            f"iperf3_received_bytes{{{labels}}} {result.received_bytes}",
            "",
            "# HELP iperf3_received_seconds Total seconds spent receiving",
            "# TYPE iperf3_received_seconds gauge",
            f"iperf3_received_seconds{{{labels}}} {result.received_seconds}",
            "",
            "# HELP iperf3_retransmits Total retransmits",
            "# TYPE iperf3_retransmits gauge",
            f"iperf3_retransmits{{{labels}}} {result.retransmits}",
            ""
        ]

        return "\n".join(metrics)
