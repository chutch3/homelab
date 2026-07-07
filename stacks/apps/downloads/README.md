# Downloads Stack

Torrent, Usenet, and manga download clients, all routed through a VPN.

## Prerequisites

Before deploying, ensure the following are in place on the target Swarm node:

- Node is labeled with `downloads: true` in `ansible/inventory/02-hosts.yml` under `node_labels`, and labels are synced by running:
  ```sh
  task ansible:cluster:update-labels
  ```
- iSCSI target mounted at `/mnt/iscsi/media-apps/` with subdirectories created for each service:
  - `qbittorrent/`, `deluge/`, `sabnzbd/`, `nzbget/`
  - Note: the live Kenku Postgres volume is **node-local** (Docker-managed) and is *not* an iSCSI directory — do not create one for it. Logical backups are handled by [Fiber](../fiber/).
- NAS SMB shares (`torrents`, `usenet`) are accessible from the node
- `traefik-public` external overlay network exists
- Root `.env` is populated with all `DOWNLOADS_*` variables (see [Environment variables](#environment-variables))

## Deployment

```sh
task ansible:deploy:service -- -e 'stack_name=downloads'
```

## Post-deployment: configure VPN proxy in each download client

> **Important:** The torrent and Usenet clients are NOT automatically routed through the VPN at the network level. Each client must be manually configured via its web UI to proxy outbound traffic through the Dante SOCKS5 proxy running in the `vpn` container. Without this, download traffic bypasses the VPN entirely.

Configure each client to use:

| Setting | Value |
|---|---|
| Proxy type | SOCKS5 |
| Host | `vpn` (or the Swarm node IP from outside the stack) |
| Port | `1080` |

## Services

| Service | Container(s) | Purpose | URL | Auth |
|---|---|---|---|---|
| qBittorrent | `qbittorrent` | Torrent client | `qbittorrent.<BASE_DOMAIN>` | Authentik |
| Deluge | `deluge` | Torrent client | `deluge.<BASE_DOMAIN>` | Authentik |
| SABnzbd | `sabnzbd` | Usenet client | `sabnzbd.<BASE_DOMAIN>` | Authentik |
| NZBGet | `nzbget` | Usenet client | `nzbget.<BASE_DOMAIN>` | Authentik |
| FlareSolverr | `downloads-flaresolverr` | Cloudflare bypass | internal only (`flaresolverr:8191`) | none |
| Kenku | `kenku` | Manga downloader — UI + REST API (port 6531) | `kenku.<BASE_DOMAIN>` | Authentik |
| Kenku DB | `kenku-pg` | Postgres database (backed up by Fiber) | internal only | none |

## How it works

### VPN (Gluetun + Dante)

[Gluetun](https://github.com/qdm12/gluetun) manages the VPN tunnel and exposes two proxies to the `downloads-internal` network:

- **HTTP proxy** on port `8888` — used automatically by FlareSolverr and Kenku via `HTTP_PROXY=http://vpn:8888`
- **SOCKS5 proxy** on port `1080` — provided by Dante, must be configured manually in each download client's UI (see [Post-deployment](#post-deployment-configure-vpn-proxy-in-each-download-client))

Port `1080` is also published to the host, so the SOCKS5 proxy is reachable from anywhere on the LAN — not just from within the stack.

Dante is not a native Gluetun feature. It is installed and started at runtime via `scripts/init-vpn.sh`, which overrides the container entrypoint, installs `dante-server` via `apk`, writes `/etc/sockd.conf`, waits for the `tun0` interface to come up, then hands off to the normal Gluetun entrypoint.

### Networks

- **`traefik-public`** — shared external network; gives Traefik access to route HTTPS traffic to the web UIs
- **`downloads-internal`** — isolated overlay network for inter-service communication (VPN proxies, FlareSolverr, Kenku + its DB)

### Storage

| Volume | Type | Backend |
|---|---|---|
| `torrents` | CIFS (SMB) | NAS share — mounted at `/data/torrents` in clients, `/Manga` in Kenku |
| `usenet` | CIFS (SMB) | NAS share — mounted at `/data/usenet` in clients |
| `qbittorrent`, `deluge`, `sabnzbd`, `nzbget` | local bind mount | `/mnt/iscsi/media-apps/<service>/` — directories on the iSCSI-mounted filesystem |
| `kenku_pg` | **node-local** Docker volume | Live Postgres data — kept **off** the OCFS2 cluster FS (Docker-managed on the pinned node). Not backed up at the file level; Fiber dumps it logically (see below). |

> **Known inconsistency:** The CIFS mount options hardcode `uid=1000,gid=1000` rather than using `${PUID}`/`${PGID}`. These must be kept in sync manually if the UID/GID changes.

> **Database storage pattern:** A live Postgres data directory must not sit on the OCFS2 cluster FS, and a file-level snapshot of a running `PGDATA` is not a valid backup. So the live volume is **node-local** (off `/mnt/iscsi`, never touched by Kopia), and **[Fiber](../fiber/)** takes consistent logical dumps via `fiber.*` labels on `kenku-pg`, writing them to the Bowl on `/mnt/iscsi`, which Kopia's `app-data` policy backs up offsite. This is the standard pattern across all DB-backed stacks (Fiber replaced the old per-stack `pg_dump` sidecars).

### FlareSolverr

This stack runs its own FlareSolverr instance separate from any other stack so that it sits inside `downloads-internal` and can reach the VPN HTTP proxy. It is reachable at `http://flaresolverr:8191` and is referenced directly in `kenku/settings.json`.

### Kenku

Two containers make up Kenku:

- `kenku-pg` — Postgres database, internal only (live data on a node-local volume — see [Storage](#storage)); backed up by Fiber via `fiber.*` labels
- `kenku` — single image serving the web UI **and** the REST API on port `6531` (same origin); routes all outbound traffic through `HTTP_PROXY=http://vpn:8888`

Static configuration (download path, naming scheme, concurrency limits, FlareSolverr URL) lives in `kenku/settings.json` and is injected as a Docker config at `/usr/share/kenku-api/settings.json`. Downloaded manga lands at `/Manga/manga` inside the container, which maps to the `torrents` NAS share.

> The image is pinned by digest to [`ghcr.io/chutch3/kenku`](https://github.com/chutch3/kenku) (a self-maintained fork). Bump the digest in `docker-compose.yml` to update.

**Restore from a Fiber dump** (custom-format `pg_dump` in the Bowl):

```sh
# Fiber writes dumps to /mnt/iscsi/app-data/fiber/bowl/downloads_kenku-pg/<timestamp>.dump
docker exec -i kenku-pg pg_restore -U ${DOWNLOADS_KENKU_DB_USER} -d ${DOWNLOADS_KENKU_DB_NAME} \
  --clean --no-owner < /mnt/iscsi/app-data/fiber/bowl/downloads_kenku-pg/<timestamp>.dump
```

## Callouts

> **Security: `DOWNLOADS_KENKU_DB_PASSWORD` is currently set to `postgres`.**
> Change this to a real password in `.env` before exposing the stack to any untrusted network.

- **Dante starts after `tun0` is ready** — `init-vpn.sh` polls for the `tun0` interface every 2 seconds before starting `sockd`. The script runs in the background so Gluetun starts immediately; Dante follows once the tunnel is established.

- **SABnzbd host whitelist** — SABnzbd rejects requests from hostnames not in its whitelist. `sabnzbd/99-fix-whitelist` runs at container startup: waits 15 seconds, patches `host_whitelist` in `sabnzbd.ini` to add `sabnzbd.<BASE_DOMAIN>`, then restarts SABnzbd via its API. A marker file (`/config/.whitelist-fixed`) prevents re-patching on subsequent restarts.

- **Docker config naming** — Docker configs are immutable once created. Updating `kenku/settings.json` requires renaming the config (e.g. `kenku_settings_v2`) and updating both the `configs:` block and the `kenku` service reference, otherwise the old config will continue to be used.

- **`settings.json` field names** — the correct field for image quality is `ImageCompression` (int, 1–100), not `QualityFactor` or `CompressImages` (old names that no longer exist). Unknown fields are silently ignored by JSON deserialization, causing `ImageCompression` to default to `0` and every download to fail with `Quality factor must be in [1..100] range`. Setting `"ImageCompression": 100` skips re-encoding entirely and saves raw source images.

- **All services are pinned to `node.labels.downloads == true`** — every container in this stack must run on the same node. The iSCSI bind mounts and VPN network routing both depend on co-location. Node labels are managed in `ansible/inventory/02-hosts.yml` under `node_labels` and synced with `task ansible:cluster:update-labels` — do not set them manually with `docker node update` as they will drift from inventory.

- **Usenet clients (NZBGet, SABnzbd) do not route downloads through the VPN** — the opt-in VPN path here is the Dante SOCKS5 proxy (`vpn:1080`), and only BitTorrent clients (Deluge, qBittorrent) can tunnel their actual download traffic through it. NZBGet/SABnzbd have no SOCKS5 option for their NNTP news-server connections, so their article downloads egress directly via the node gateway regardless of any proxy setting in the UI. This is by design, not a missed configuration step — use **SSL/TLS to your Usenet provider** (typically port 563) instead, which encrypts content against your ISP. Unlike BitTorrent there is no peer swarm advertising your IP, so the VPN buys little here. To genuinely force these clients through the tunnel you'd need network-level routing (`network_mode: service:vpn`), which Swarm does not support.

## Environment variables

All stack-specific variables are prefixed `DOWNLOADS_` in the root `.env`. All are required — no defaults are set in the compose file. Shared variables (`TZ`, `BASE_DOMAIN`, `PUID`, `PGID`, `SMB_*`, `NAS_SERVER`, `LOCAL_SUBNET`) are unprefixed.

| Variable | Used by | Description |
|---|---|---|
| `DOWNLOADS_VPN_SERVICE_PROVIDER` | vpn | VPN provider name (e.g. `nordvpn`) |
| `DOWNLOADS_VPN_TYPE` | vpn | Protocol (`openvpn` or `wireguard`) |
| `DOWNLOADS_OPENVPN_USER` | vpn | VPN service username |
| `DOWNLOADS_OPENVPN_PASSWORD` | vpn | VPN service password |
| `DOWNLOADS_VPN_SERVER_COUNTRIES` | vpn | Comma-separated country filter |
| `DOWNLOADS_VPN_SERVER_CATEGORIES` | vpn | Server category filter (e.g. `P2P`) |
| `DOWNLOADS_VPN_SERVER_CITIES` | vpn | Comma-separated city filter |
| `DOWNLOADS_GATEWAY_IP` | vpn | LAN gateway IP used as DNS inside the VPN container |
| `DOWNLOADS_DOCKER_SUBNET` | vpn | Docker overlay subnet allowed through the VPN firewall |
| `DOWNLOADS_FLARESOLVERR_LOG_LEVEL` | flaresolverr | Log verbosity (`info`, `debug`, etc.) |
| `DOWNLOADS_KENKU_DB_USER` | kenku-pg, kenku | Postgres username |
| `DOWNLOADS_KENKU_DB_NAME` | kenku-pg, kenku | Postgres database name |
| `DOWNLOADS_KENKU_DB_PASSWORD` | kenku-pg, kenku | Postgres password — **do not leave as `postgres`** |
