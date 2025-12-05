# Grafana Dashboards

This directory contains the Grafana dashboard provisioning configuration.

## Dashboard Storage

Dashboards are stored in two locations:

1. **NAS CIFS Mount** (`/etc/grafana/provisioning/dashboards` inside Grafana container)
   - Mounted from `${NAS_SERVER}/grafana_dashboards`
   - User-managed dashboards go here
   - Changes persist across deployments
   - Can be edited via Grafana UI

2. **Local Dashboards** (`/etc/grafana/provisioning/dashboards/local` inside Grafana container)
   - Mounted from `./dashboards/local` directory
   - Pre-configured dashboards for homelab monitoring
   - Read-only (cannot be edited via UI)
   - Version controlled with the repository

## Adding Dashboards

### Method 1: Via Grafana UI (Recommended)
1. Create or import a dashboard in Grafana
2. Click "Save dashboard"
3. Dashboard is automatically saved to the NAS mount

### Method 2: Manual JSON Upload to NAS
1. Export dashboard as JSON from Grafana
2. Copy JSON file to NAS: `/grafana_dashboards/*.json`
3. Grafana will auto-discover and load it within 30 seconds

### Method 3: Add to Repository (For Built-in Dashboards)
1. Place JSON file in `./dashboards/local/`
2. Commit to repository
3. Redeploy monitoring stack

## Recommended Dashboards

We recommend importing these community dashboards:

- **Node Exporter Full**: Dashboard ID `1860` (host metrics)
- **Docker and System Monitoring**: Dashboard ID `893` (container metrics)
- **cAdvisor**: Dashboard ID `14282` (detailed container stats)

### Import via Grafana UI:
1. Go to Grafana → Dashboards → Import
2. Enter dashboard ID
3. Select "Prometheus" as data source
4. Click Import

## Dashboard Development

To create custom dashboards:

1. Use Grafana UI to design dashboard
2. Test with live Prometheus data
3. Export as JSON
4. (Optional) Add to `./dashboards/local/` for version control

## Troubleshooting

**Dashboards not appearing:**
- Check NAS mount: `docker exec <grafana-container> ls -la /etc/grafana/provisioning/dashboards`
- Verify JSON syntax: `cat dashboard.json | jq .`
- Check Grafana logs: `docker service logs monitoring_grafana`

**Permission issues:**
- Ensure Grafana can read NAS mount
- Check CIFS credentials in `.env` file
