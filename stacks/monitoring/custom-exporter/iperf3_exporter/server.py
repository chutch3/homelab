"""
HTTP server module

Handles HTTP requests and coordinates test execution.
"""
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Callable

from iperf3_exporter.runner import IPerf3Runner
from iperf3_exporter.metrics import PrometheusMetricsFormatter


def create_probe_handler(runner: IPerf3Runner, formatter: PrometheusMetricsFormatter) -> Callable:
    """
    Factory function to create a ProbeHandler class with injected dependencies.

    Args:
        runner: IPerf3Runner instance for executing iperf3 tests
        formatter: PrometheusMetricsFormatter instance for formatting metrics

    Returns:
        ProbeHandler class with dependencies injected
    """

    class ProbeHandler(BaseHTTPRequestHandler):
        """HTTP request handler for probe endpoint"""

        def do_GET(self):
            """Handle GET requests"""
            parsed_path = urlparse(self.path)

            if parsed_path.path == "/probe":
                self.handle_probe(parsed_path)
            elif parsed_path.path == "/health":
                self.handle_health()
            elif parsed_path.path == "/":
                self.handle_index()
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found\n")

        def handle_probe(self, parsed_path):
            """Handle probe requests"""
            params = parse_qs(parsed_path.query)

            # Validate target parameter
            if "target" not in params:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing required parameter: target\n")
                return

            target = params["target"][0]
            port = int(params.get("port", ["5201"])[0])
            period = int(params.get("period", ["5"])[0])

            # Parse host:port format if provided
            if ":" in target:
                host, target_port = target.rsplit(":", 1)
                port = int(target_port)
            else:
                host = target

            # Run iperf3 test
            result = runner.run_test(host, port, period)

            # Format metrics
            metrics = formatter.format(result, target, port)

            # Send response
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(metrics.encode())

        def handle_health(self):
            """Handle health check requests"""
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK\n")

        def handle_index(self):
            """Handle index page requests"""
            html = b"""<!DOCTYPE html>
<html>
<head><title>iPerf3 Exporter</title></head>
<body>
<h1>iPerf3 Prometheus Exporter</h1>
<p><a href="/probe?target=localhost:5201">Probe localhost:5201</a></p>
<p><a href="/health">Health Check</a></p>
</body>
</html>
"""
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(html)

        def log_message(self, format, *args):
            """Log HTTP requests to stdout"""
            sys.stdout.write("%s - - [%s] %s\n" %
                            (self.address_string(),
                             self.log_date_time_string(),
                             format % args))

    return ProbeHandler


def run_server(host: str = "", port: int = 9579, iperf3_path: str = "iperf3"):
    """
    Run the HTTP server.

    Args:
        host: Host to bind to (empty string for all interfaces)
        port: Port to listen on
        iperf3_path: Path to iperf3 binary
    """
    # Create dependencies
    runner = IPerf3Runner(iperf3_path=iperf3_path)
    formatter = PrometheusMetricsFormatter()

    # Create handler with injected dependencies
    handler_class = create_probe_handler(runner, formatter)

    server_address = (host, port)
    httpd = HTTPServer(server_address, handler_class)

    print(f"Starting iPerf3 exporter on {host or '0.0.0.0'}:{port}...")
    print(f"Using iperf3 binary: {iperf3_path}")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        httpd.shutdown()
