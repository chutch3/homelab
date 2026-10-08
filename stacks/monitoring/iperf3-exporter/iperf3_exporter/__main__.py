"""
Main entry point for the iperf3 exporter.
"""
import argparse
import sys

from .server import run_server


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="iPerf3 Prometheus Exporter"
    )
    parser.add_argument(
        "--host",
        default="",
        help="Host to bind to (default: all interfaces)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9579,
        help="Port to listen on (default: 9579)"
    )
    parser.add_argument(
        "--iperf3-path",
        default="iperf3",
        help="Path to iperf3 binary (default: iperf3)"
    )

    args = parser.parse_args()

    try:
        run_server(
            host=args.host,
            port=args.port,
            iperf3_path=args.iperf3_path
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
