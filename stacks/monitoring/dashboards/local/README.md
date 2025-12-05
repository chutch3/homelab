# Homelab Grafana Dashboards

This directory contains version-controlled Grafana dashboards for the homelab monitoring stack.

## Available Dashboards

### Node Resources Dashboard (`node-resources.json`)

Comprehensive monitoring dashboard for all Docker Swarm nodes showing:

**System Metrics:**
- CPU Usage by Node (%)
- Memory Usage by Node (%)
- Disk Usage by Node (Root filesystem, %)
- Network I/O by Node (bytes/sec, showing receive and transmit)
- System Load Average (1m, 5m, 15m)
- Node Uptime

**Container Metrics:**
- Running Containers by Node (count)
- Container Memory Usage by Node (bytes)
- Container CPU Usage by Node (%)

**Current Status:**
- Bar gauge showing current CPU and RAM usage across all nodes

**Features:**
- Auto-refresh every 30 seconds
- Time range: Last 1 hour (configurable)
- Legend showing last and max values for easy reference
- Color-coded thresholds (green/yellow/red)

## Data Sources

All dashboards use the following Prometheus data sources:

1. **Node Exporter** - Host-level metrics (CPU, memory, disk, network)
   - Metrics: `node_*`
   - Port: 9100
   - Deployed as global service (one per node)

2. **cAdvisor** - Container-level metrics
   - Metrics: `container_*`
   - Port: 8080
   - Deployed as global service (one per node)

3. **Docker Daemon** - Docker engine metrics
   - Metrics: `engine_*`
   - Port: 9323
   - Requires daemon metrics configuration

## Deployment

Dashboards in this directory are automatically provisioned to Grafana via the dashboard provisioning configuration at `/etc/grafana/provisioning/dashboards/dashboards.yml`.

The dashboards appear in Grafana under the "Homelab" folder.

## Customization

You can customize these dashboards in two ways:

1. **Version-controlled (recommended):** Edit the JSON files directly in this directory
   - Changes are tracked in git
   - Automatically reloaded by Grafana
   - Shared across team/deployments

2. **In Grafana UI:** Make changes in the Grafana interface
   - Changes are saved to the CIFS mount at `/mnt/nas/grafana/dashboards/`
   - Not version-controlled
   - Specific to this deployment

## Metrics Reference

### Node Exporter Queries

```promql
# CPU Usage (%)
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory Usage (%)
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))

# Disk Usage (%)
100 - ((node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"}) * 100)

# Network I/O (bytes/sec)
rate(node_network_receive_bytes_total{device!~"lo|veth.*|docker.*"}[5m])
rate(node_network_transmit_bytes_total{device!~"lo|veth.*|docker.*"}[5m])

# System Load
node_load1
node_load5
node_load15

# Uptime
node_time_seconds - node_boot_time_seconds
```

### cAdvisor Queries

```promql
# Running Containers
count by (instance) (container_last_seen{name=~".+"})

# Container Memory Usage
sum by (instance) (container_memory_usage_bytes{name=~".+"})

# Container CPU Usage (%)
sum by (instance) (rate(container_cpu_usage_seconds_total{name=~".+"}[5m])) * 100
```

## Troubleshooting

### Dashboard not showing data

1. Check Prometheus is scraping targets:
   ```bash
   docker exec monitoring_prometheus_<id> wget -qO- http://localhost:9090/api/v1/targets
   ```

2. Verify Node Exporter is running on all nodes:
   ```bash
   docker service ps monitoring_node-exporter
   ```

3. Verify cAdvisor is running on all nodes:
   ```bash
   docker service ps monitoring_cadvisor
   ```

### Metrics missing from specific node

1. Check if the service is running on that node:
   ```bash
   docker service ps monitoring_node-exporter --filter "node=<node-name>"
   ```

2. Test if the metrics endpoint is accessible:
   ```bash
   curl http://<node-ip>:9100/metrics
   curl http://<node-ip>:8080/metrics
   ```

### Dashboard shows "No Data"

1. Verify time range is appropriate (default: last 1 hour)
2. Check that Prometheus datasource is configured correctly
3. Verify scrape interval in Prometheus configuration (default: 15s)

## Adding New Panels

To add new monitoring panels:

1. Copy an existing panel in the JSON
2. Update the panel ID (must be unique)
3. Update the gridPos (x, y, w, h) for layout
4. Modify the Prometheus query in targets[].expr
5. Update title and legend format

Example panel structure:
```json
{
  "id": <unique-id>,
  "title": "Panel Title",
  "type": "timeseries",
  "gridPos": {
    "h": 8,
    "w": 12,
    "x": 0,
    "y": 0
  },
  "targets": [
    {
      "expr": "<prometheus-query>",
      "legendFormat": "{{instance}}"
    }
  ]
}
```

## Dashboard IDs

- `homelab-node-resources`: Node resource monitoring dashboard (UID)

## Version History

- v1.0.0 (2024-12-04): Initial dashboard with CPU, memory, disk, network, and container metrics
