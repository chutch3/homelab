"""
iPerf3 runner module

Handles execution of iperf3 commands and parsing of results.
"""
import json
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class IPerf3Result:
    """Result from an iperf3 test run"""
    success: bool
    sent_bytes: int = 0
    sent_seconds: float = 0.0
    received_bytes: int = 0
    received_seconds: float = 0.0
    retransmits: int = 0
    error: Optional[str] = None


class IPerf3Runner:
    """Runs iperf3 tests and parses results"""

    def __init__(self, iperf3_path: str = "iperf3", timeout_offset: int = 10):
        """
        Initialize the runner.

        Args:
            iperf3_path: Path to iperf3 binary
            timeout_offset: Extra seconds to add to test duration for subprocess timeout
        """
        self.iperf3_path = iperf3_path
        self.timeout_offset = timeout_offset

    def run_test(self, host: str, port: int = 5201, duration: int = 5) -> IPerf3Result:
        """
        Run an iperf3 test against a target.

        Args:
            host: Target hostname or IP
            port: Target port
            duration: Test duration in seconds

        Returns:
            IPerf3Result with test results
        """
        try:
            result = subprocess.run(
                [
                    self.iperf3_path,
                    "-c", host,
                    "-p", str(port),
                    "-t", str(duration),
                    "-J"  # JSON output
                ],
                capture_output=True,
                text=True,
                timeout=duration + self.timeout_offset
            )

            if result.returncode != 0:
                return IPerf3Result(
                    success=False,
                    error=f"iperf3 exited with code {result.returncode}: {result.stderr}"
                )

            return self._parse_json_output(result.stdout)

        except subprocess.TimeoutExpired:
            return IPerf3Result(
                success=False,
                error=f"Test timed out after {duration + self.timeout_offset} seconds"
            )
        except FileNotFoundError:
            return IPerf3Result(
                success=False,
                error=f"iperf3 binary not found at: {self.iperf3_path}"
            )
        except Exception as e:
            return IPerf3Result(
                success=False,
                error=f"Unexpected error: {str(e)}"
            )

    def _parse_json_output(self, json_output: str) -> IPerf3Result:
        """
        Parse iperf3 JSON output.

        Args:
            json_output: JSON string from iperf3

        Returns:
            IPerf3Result with parsed data
        """
        try:
            data = json.loads(json_output)
            end_data = data.get("end", {})
            sum_sent = end_data.get("sum_sent", {})
            sum_received = end_data.get("sum_received", {})

            return IPerf3Result(
                success=True,
                sent_bytes=sum_sent.get("bytes", 0),
                sent_seconds=sum_sent.get("seconds", 0.0),
                received_bytes=sum_received.get("bytes", 0),
                received_seconds=sum_received.get("seconds", 0.0),
                retransmits=sum_sent.get("retransmits", 0)
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            return IPerf3Result(
                success=False,
                error=f"Failed to parse iperf3 output: {str(e)}"
            )
