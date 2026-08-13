# Gamarr Stack

Game and ROM manager (Radarr/Sonarr-style) — searches indexers via the shared Prowlarr, grabs via qBittorrent or SABnzbd, and organizes into a dedicated NAS library that [RomM](../romm/) reads read-only.

## Prerequisites

- `traefik-public` external overlay network exists
- Root `.env` populated with all `GAMARR_*` variables (see [Environment variables](#environment-variables))
- Dedicated `//NAS/games` share exists on a pool with free space (**not** the full `all_data` pool)

## Deployment

```sh
task ansible:deploy:service -- -e 'stack_name=gamarr'
```

## Image

`image:` points at a self-maintained fork build (`ghcr.io/chutch3/gamarr`), not upstream. Base is [`JeremiahM37/gamarr`](https://github.com/JeremiahM37/gamarr) `main` with three local patches not yet merged upstream:

1. Upstream `main`'s HTTP 204 login fix (tagged releases reject qBittorrent >= 5.2's 204 success response)
2. Usenet-via-Prowlarr routing (`7dafdab`) — tags each Prowlarr result by protocol and routes usenet grabs to SABnzbd instead of qBittorrent
3. Vimm session-cookie fix (`3a32848`) — carries the vault-page cookie into the download POST so Vimm stops 400-rejecting grabs

The currently pinned tag may be further ahead of these three (check the tag suffix against the fork's commit log). Rebuild and repush from the clone at `~/workspace/gamarr` when upstream lands these; switch the image back to a tagged upstream release at that point.

## How it works

### Sources registry (`sources.json`)

Myrient (the previous DDL source) shut down 2026-03-31. `sources.json` repoints the "Myrient" driver at archive.org No-Intro/Redump mirrors and Vimm's vault instead. Pre-flight renders it to the config dir; `GAMARR_SOURCES_PATH` points the app at it.

### Indexers

Shared Prowlarr, same instance as Radarr/Sonarr. `PROWLARR_GAME_INDEXERS` can list torrent **and** usenet indexer IDs together — this fork tags each result by protocol and routes usenet grabs to SABnzbd automatically.

### Download clients

- **qBittorrent** (shared, behind the downloads VPN) — `QB_SAVE_PATH=/data/torrents/games` is the path as qBittorrent sees it (it mounts the torrents share at `/data/torrents`); completed downloads land under `games/` there, and gamarr (mounting the same share) organizes them into the library.
- **SABnzbd** (shared) — usenet grabs route here; only active once `GAMARR_SABNZBD_API_KEY` is set (needs both URL and key).

### Library layout

Dedicated `//NAS/games` share, mounted at `/data/games`. gamarr runs as root and creates `vault/` (PC games) and `roms/` on first import. A separate step (`task gamarr:sync-roms`, see `scripts/sync-roms-to-sdcard.sh`) exports `roms/` to a removable SD card by filesystem label — see the script's `--help` for usage.

### RomM integration

`ROMM_URL` sets the link target for the RomM button in gamarr's UI. [RomM](../romm/) mounts the same `roms/` path read-only to browse/play what gamarr organizes.

### Metadata

`RAWG_API_KEY` is optional — blank disables the release calendar and cover art.

## Callouts

- **Config placement** — `gamarr_config` is a bind mount on the iSCSI app-data LUN, which is only mounted on the manager node. The service is pinned to `node.role == manager` so the bind always resolves and the task can't land on a worker holding a stale volume.

## Environment variables

All stack-specific variables are prefixed `GAMARR_` in the root `.env`. Shared variables (`TZ`, `BASE_DOMAIN`, `SMB_*`, `NAS_SERVER`) are unprefixed.

| Variable | Description |
|---|---|
| `GAMARR_PROWLARR_API_KEY` | Prowlarr API key (required) |
| `GAMARR_PROWLARR_GAME_INDEXERS` | Comma-separated Prowlarr indexer IDs, torrent and/or usenet (default: `7,5,15,9,8,3,4`) |
| `GAMARR_QB_USER` / `GAMARR_QB_PASS` | qBittorrent credentials |
| `GAMARR_SABNZBD_API_KEY` | SABnzbd API key — usenet routing stays inactive without it |
| `GAMARR_RAWG_API_KEY` | Optional; blank disables release calendar/cover art |
