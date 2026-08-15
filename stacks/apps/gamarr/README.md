# Gamarr Stack

Game and ROM manager (Radarr/Sonarr-style). Runs **DDL-only**: it fetches games directly over HTTP from the sources in `sources.json` (archive.org No-Intro/Redump mirrors and Vimm's vault) and organizes them into a dedicated NAS library that [RomM](../romm/) reads read-only. No indexers, torrent, or usenet clients are involved.

## Prerequisites

- `traefik-public` external overlay network exists
- Root `.env` populated with the `GAMARR_*` variables (only `GAMARR_RAWG_API_KEY`, optional — see [Environment variables](#environment-variables))
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

### Downloads (DDL)

Downloads are direct HTTP fetches gamarr performs itself — no torrent or usenet client. Prowlarr (blank API key) and SABnzbd (blank URL/key) are off, so no indexer or usenet grabs happen. qBittorrent can't be turned off by blanking `QB_URL` — the app falls back to a default URL when the var is empty — so instead `WATCHER_ENABLED=false` disables the torrent completion poller; the qB client is then never invoked (its only caller runs on torrent-protocol results, which never occur without an indexer).

Each fetch stages onto a **node-local scratch volume** (`gamarr_staging`, mounted at `/data/staging` = `QB_SAVE_PATH`, off both CIFS and iSCSI), then gamarr moves the finished file onto the `//NAS/games` share. The stage→import step is a cross-device move (local → CIFS), handled by the fork's buffered `moveFile` (upstream `io.Copy` EAGAINs on CIFS). Staging is throwaway: an interrupted DDL is deleted and re-fetched (no resume), so it need not survive a reschedule.

> **Extraction caveat:** with `EXTRACT_ARCHIVES=true`, unpack (`7z`/`unrar`) runs at the *destination* on `//NAS/games`, not in local staging — so local staging speeds the download write but the unpack still runs over SMB. Extract-in-staging would need a fork change.

### Library layout

Dedicated `//NAS/games` share, mounted at `/data/games`. gamarr runs as root and creates `vault/` (PC games) and `roms/` on first import. A separate step (`task gamarr:sync-roms`, see `scripts/sync-roms-to-sdcard.sh`) exports `roms/` to a removable SD card by filesystem label — see the script's `--help` for usage.

### RomM integration

`ROMM_URL` sets the link target for the RomM button in gamarr's UI. [RomM](../romm/) mounts the same `roms/` path read-only to browse/play what gamarr organizes.

### Metadata

`RAWG_API_KEY` is optional — blank disables the release calendar and cover art.

## Callouts

- **Config placement & floating** — `gamarr_config` is a bind on the iSCSI app-data LUN, an **OCFS2 cluster FS mounted on every node**, so the service is *not* pinned and can land anywhere. The config DB is SQLite (WAL); `replicas: 1` plus `update_config.order: stop-first` keep a single writer — the old task stops before the new one starts, so two instances never open the DB at once (a rolling update would otherwise overlap them).

## Environment variables

All stack-specific variables are prefixed `GAMARR_` in the root `.env`. Shared variables (`TZ`, `BASE_DOMAIN`, `NAS_SERVER`) are unprefixed.

| Variable | Description |
|---|---|
| `GAMARR_RAWG_API_KEY` | Optional; blank disables release calendar/cover art |
