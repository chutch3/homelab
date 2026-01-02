# Custom iPerf3 Prometheus Exporter

A lightweight Python-based Prometheus exporter for iperf3 network performance metrics, built with proper TDD practices.

## Features

- ✅ Proper Python package structure
- ✅ Full test coverage with pytest
- ✅ Uses iperf3 3.18 (CVE-2024-53580 fixed)
- ✅ Compatible with Prometheus blackbox exporter pattern
- ✅ Minimal dependencies (Python standard library only)

## Project Structure

```
custom-exporter/
├── src/
│   └── iperf3_exporter/
│       ├── __init__.py
│       ├── __main__.py      # Entry point
│       ├── runner.py         # iperf3 execution
│       ├── metrics.py        # Prometheus formatting
│       └── server.py         # HTTP server
├── tests/
│   ├── test_runner.py        # Unit tests for runner
│   ├── test_metrics.py       # Unit tests for metrics
│   └── test_integration.py  # Integration tests
├── pyproject.toml            # Poetry configuration
├── pytest.ini                # Pytest configuration
├── Dockerfile                # Docker build
└── README.md                 # This file
```

## Development Setup

### Prerequisites

- Python 3.8+
- Poetry (Python dependency manager)
- iperf3 (for integration testing)

### Install Poetry

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### Install Dependencies

```bash
poetry install
```

### Run Tests

```bash
# Run all tests with coverage
poetry run pytest

# Run specific test file
poetry run pytest tests/test_runner.py

# Run tests with verbose output
poetry run pytest -v

# Run tests and show coverage report
poetry run pytest --cov-report=term-missing
```

## Running Locally

```bash
# Run the exporter
poetry run iperf3-exporter

# Or with Python module syntax
poetry run python -m iperf3_exporter

# With custom options
poetry run iperf3-exporter --port 9580 --iperf3-path /usr/local/bin/iperf3
```

## API

### Endpoints

- `GET /probe?target=<host:port>` - Run iperf3 test and return metrics
- `GET /health` - Health check endpoint
- `GET /` - Index page with links

### Query Parameters

- `target` (required) - Target host:port or just host (default port 5201)
- `port` (optional) - Override port (default: 5201)
- `period` (optional) - Test duration in seconds (default: 5)

### Example

```bash
curl "http://localhost:9579/probe?target=192.168.86.41:5201&period=5"
```

## Metrics Exported

- `iperf3_up` - Was the last probe successful (1=success, 0=failure)
- `iperf3_sent_bytes` - Total sent bytes
- `iperf3_sent_seconds` - Total seconds spent sending
- `iperf3_received_bytes` - Total received bytes
- `iperf3_received_seconds` - Total seconds spent receiving
- `iperf3_retransmits` - Total TCP retransmits

## Docker

### Building

```bash
docker build -t custom-iperf3-exporter:latest .
```

### Running

```bash
docker run -p 9579:9579 custom-iperf3-exporter:latest
```

## Prometheus Configuration

Use the same configuration as edgard/iperf3_exporter:

```yaml
scrape_configs:
  - job_name: "iperf3-bandwidth"
    metrics_path: /probe
    scrape_interval: 30m
    scrape_timeout: 5m
    dockerswarm_sd_configs:
      - host: unix:///var/run/docker.sock
        role: nodes
    relabel_configs:
      - source_labels: [__meta_dockerswarm_node_address]
        target_label: __param_target
        replacement: $1:5201
      - source_labels: [__meta_dockerswarm_node_hostname]
        target_label: instance
      - target_label: __address__
        replacement: localhost:9579
```

## Testing

The project follows TDD principles with comprehensive test coverage:

- **Unit Tests**: Test individual components (runner, metrics formatter)
- **Integration Tests**: Test HTTP endpoints and full workflow
- **Mocking**: Uses pytest-mock for subprocess isolation

### Test Coverage

Run tests with coverage report:

```bash
poetry run pytest --cov-report=html
open htmlcov/index.html  # View coverage report
```

## Why This Custom Exporter?

The official `edgard/iperf3_exporter` uses iperf3 3.17.1, which has CVE-2024-53580 causing segmentation faults. This custom exporter:

1. Uses iperf3 3.18 (CVE fixed)
2. Has full test coverage
3. Simple codebase you can modify
4. Drop-in replacement for edgard/iperf3_exporter

## License

MIT
