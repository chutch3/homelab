# Status Pipeline

Pushes Uptime Kuma service status data from the homelab to a publicly accessible MinIO bucket, exposed via Tailscale Funnel, so a portfolio site can fetch and display live service uptime.

## Architecture

```
[Uptime Kuma] → [cron on NAS] → [MinIO bucket] → [Tailscale Funnel] → [public internet]
   internal        every 15m        NAS               NAS                 read-only JSON
```

All components run inside the homelab. Tailscale Funnel is the only public surface — serving a single read-only JSON file at `/public-status/status.json`.

## Prerequisites

- **NAS**: OpenMediaVault with MinIO installed
- **Uptime Kuma**: Running with a published status page
- **Tailscale**: Installed on NAS with `tag:homelab-nas` and Funnel enabled
- **SSH access**: Root SSH to the NAS from the machine running setup
- **Tools on NAS**: `wget`, `jq`, `openssl` (standard on Debian/OMV)

## Environment Variables

All variables are prefixed with `STATUS_PIPELINE_` and defined in `.env`:

| Variable | Description |
|---|---|
| `STATUS_PIPELINE_STATUS_SLUG` | Uptime Kuma status page slug (e.g., `homelab`) |
| `STATUS_PIPELINE_MINIO_ACCESS_KEY` | MinIO root user |
| `STATUS_PIPELINE_MINIO_SECRET_KEY` | MinIO root password |
| `STATUS_PIPELINE_URL` | Public Funnel URL (set after enabling Funnel) |

Also requires `NAS_SERVER`, `NAS_USER`, `BASE_DOMAIN`, and `SSH_KEY_FILE` from the homelab `.env`.

## Setup

```bash
# 1. Configure .env with the variables above

# 2. Upload the updated Tailscale ACL policy (adds tag:homelab-nas + Funnel)
#    https://login.tailscale.com/admin/acls

# 3. Install Tailscale on the NAS (one-off)
./tools/status-pipeline/setup-nas-tailscale.sh

# 4. Deploy sync script, create MinIO bucket, register OMV cron job
task status-pipeline:setup

# 5. Enable Tailscale Funnel
task status-pipeline:funnel:on

# 6. Set STATUS_PIPELINE_URL in .env with the Funnel URL from step 5

# 7. Verify the full pipeline
task status-pipeline:verify
```

## Tasks

| Task | Description |
|---|---|
| `status-pipeline:setup` | Deploy sync script + cron to NAS |
| `status-pipeline:update` | Update sync script on NAS (preserves config/cron) |
| `status-pipeline:verify` | Run one-shot sync and check public endpoint |
| `status-pipeline:logs` | Tail the sync log on NAS |
| `status-pipeline:funnel:on` | Enable Tailscale Funnel |
| `status-pipeline:funnel:off` | Disable Tailscale Funnel (killswitch) |
| `status-pipeline:funnel:status` | Show Funnel status |
| `status-pipeline:cron:remove` | Remove the OMV cron job |

## Monitoring (Optional)

A Grafana dashboard (`stacks/monitoring/dashboards/local/status-pipeline.json`) tracks MinIO request rate, bandwidth, and errors for the `public-status` bucket.

To enable Prometheus scraping, update `stacks/monitoring/prometheus.yml` and replace `REPLACE_WITH_NAS_SERVER` with your NAS hostname in the `minio` scrape job.

## Security

- **Public surface**: One read-only JSON file behind Tailscale Funnel HTTPS
- **Path-restricted**: Funnel only exposes `/public-status/`, not the full MinIO API
- **No inbound ports**: Funnel is outbound-initiated from the NAS
- **Credentials**: Stored in `.env` (gitignored) and `/etc/status-pipeline.conf` on the NAS (mode 600)
- **Killswitch**: `task status-pipeline:funnel:off`

## Data Shape

The JSON at the public URL contains:

- `publicGroupList` — monitor groups and their names
- `heartbeatList` — ~50 timestamped heartbeats per monitor (1-min intervals)
- `uptimeList` — 24-hour uptime percentages per monitor
- `config` — status page metadata
- `incident` / `maintenanceList` — active incidents and maintenance windows

## Files

| File | Description |
|---|---|
| `sync-status.sh` | Runs on NAS — fetches Uptime Kuma, uploads to MinIO |
| `setup-nas.sh` | Deploys sync script + cron to NAS via SSH |
| `setup-nas-tailscale.sh` | One-off Tailscale install on NAS |
| `remove-cron.sh` | Removes the OMV cron job |
| `bucket-policy.json` | S3 anonymous read policy for `public-status/status.json` |
| `Taskfile.yml` | Task definitions |
