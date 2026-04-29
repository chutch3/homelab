# Downloads Stack

Torrent, Usenet, and manga download clients, all routed through a VPN.

## Prerequisites

Before deploying, ensure the following are in place on the target Swarm node:

- Node is labeled with `downloads: true` in `ansible/inventory/02-hosts.yml` under `node_labels`, and labels are synced by running:
  ```sh
  task ansible:cluster:update-labels
  ```
- iSCSI target mounted at `/mnt/iscsi/media-apps/` with subdirectories created for each service:
  - `qbittorrent/`, `deluge/`, `sabnzbd/`, `nzbget/`, `tranga-pg/`
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
| Tranga | `tranga-website` | Manga downloader UI | `tranga.<BASE_DOMAIN>` | Authentik |
| Tranga API | `tranga-api` | REST API (port 6531) | internal only | none |
| Tranga DB | `tranga-pg` | Postgres database | internal only | none |

## How it works

### VPN (Gluetun + Dante)

[Gluetun](https://github.com/qdm12/gluetun) manages the VPN tunnel and exposes two proxies to the `downloads-internal` network:

- **HTTP proxy** on port `8888` — used automatically by FlareSolverr and Tranga via `HTTP_PROXY=http://vpn:8888`
- **SOCKS5 proxy** on port `1080` — provided by Dante, must be configured manually in each download client's UI (see [Post-deployment](#post-deployment-configure-vpn-proxy-in-each-download-client))

Port `1080` is also published to the host, so the SOCKS5 proxy is reachable from anywhere on the LAN — not just from within the stack.

Dante is not a native Gluetun feature. It is installed and started at runtime via `scripts/init-vpn.sh`, which overrides the container entrypoint, installs `dante-server` via `apk`, writes `/etc/sockd.conf`, waits for the `tun0` interface to come up, then hands off to the normal Gluetun entrypoint.

### Networks

- **`traefik-public`** — shared external network; gives Traefik access to route HTTPS traffic to the web UIs
- **`downloads-internal`** — isolated overlay network for inter-service communication (VPN proxies, FlareSolverr, Tranga API/DB)

### Storage

| Volume | Type | Backend |
|---|---|---|
| `torrents` | CIFS (SMB) | NAS share — mounted at `/data/torrents` in clients, `/Manga` in Tranga |
| `usenet` | CIFS (SMB) | NAS share — mounted at `/data/usenet` in clients |
| `qbittorrent`, `deluge`, `sabnzbd`, `nzbget` | local bind mount | `/mnt/iscsi/media-apps/<service>/` — directories on the iSCSI-mounted filesystem |
| `tranga_pg` | local bind mount | `/mnt/iscsi/media-apps/tranga-pg/` |

> **Known inconsistency:** The CIFS mount options hardcode `uid=1000,gid=1000` rather than using `${PUID}`/`${PGID}`. These must be kept in sync manually if the UID/GID changes.

### FlareSolverr

This stack runs its own FlareSolverr instance separate from any other stack so that it sits inside `downloads-internal` and can reach the VPN HTTP proxy. It is reachable at `http://flaresolverr:8191` and is referenced directly in `tranga/settings.json`.

### Tranga

Three containers make up Tranga:

- `tranga-pg` — Postgres database, internal only
- `tranga-api` — REST API on port `6531`, routes all outbound traffic through `HTTP_PROXY=http://vpn:8888`
- `tranga-website` — web UI, proxies API calls to `http://tranga-api:6531`

Static configuration (download path, naming scheme, concurrency limits, FlareSolverr URL) lives in `tranga/settings.json` and is injected as a Docker config. Downloaded manga lands at `/Manga/manga` inside the container, which maps to the `torrents` NAS share.

> **`tranga-api` uses the `cuttingedge` image tag** rather than `latest` because the stable release does not yet include the fix for WeebCentral failing with FlareSolverr ([C9Glax/tranga#575](https://github.com/C9Glax/tranga/issues/575), fixed in PR #570). Without `cuttingedge`, WeebCentral returns 403 and FlareSolverr is never invoked. Switch to `latest` once that fix appears in a stable release.

## Callouts

> **Security: `DOWNLOADS_TRANGA_DB_PASSWORD` is currently set to `postgres`.**
> Change this to a real password in `.env` before exposing the stack to any untrusted network.

- **Dante starts after `tun0` is ready** — `init-vpn.sh` polls for the `tun0` interface every 2 seconds before starting `sockd`. The script runs in the background so Gluetun starts immediately; Dante follows once the tunnel is established.

- **SABnzbd host whitelist** — SABnzbd rejects requests from hostnames not in its whitelist. `sabnzbd/99-fix-whitelist` runs at container startup: waits 15 seconds, patches `host_whitelist` in `sabnzbd.ini` to add `sabnzbd.<BASE_DOMAIN>`, then restarts SABnzbd via its API. A marker file (`/config/.whitelist-fixed`) prevents re-patching on subsequent restarts.

- **Docker config naming** — Docker configs are immutable once created. Updating `tranga/settings.json` requires renaming the config (e.g. `tranga_settings_v2`) and updating both the `configs:` block and the `tranga-api` service reference, otherwise the old config will continue to be used.

- **`settings.json` field names** — the correct field for image quality is `ImageCompression` (int, 1–100), not `QualityFactor` or `CompressImages` (old names that no longer exist). Unknown fields are silently ignored by JSON deserialization, causing `ImageCompression` to default to `0` and every download to fail with `Quality factor must be in [1..100] range`. Setting `"ImageCompression": 100` skips re-encoding entirely and saves raw source images.

- **All services are pinned to `node.labels.downloads == true`** — every container in this stack must run on the same node. The iSCSI bind mounts and VPN network routing both depend on co-location. Node labels are managed in `ansible/inventory/02-hosts.yml` under `node_labels` and synced with `task ansible:cluster:update-labels` — do not set them manually with `docker node update` as they will drift from inventory.

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
| `DOWNLOADS_TRANGA_DB_USER` | tranga-pg, tranga-api | Postgres username |
| `DOWNLOADS_TRANGA_DB_NAME` | tranga-pg, tranga-api | Postgres database name |
| `DOWNLOADS_TRANGA_DB_PASSWORD` | tranga-pg, tranga-api | Postgres password — **do not leave as `postgres`** |
