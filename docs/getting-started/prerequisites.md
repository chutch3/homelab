# Prerequisites

## Required

- **Linux nodes** — Ubuntu 22.04+ or Debian 11+ (Docker installed by `task ansible:bootstrap`)
- **Cloudflare domain** — with wildcard A record (`*` → server IP, DNS-only/gray cloud)
- **Cloudflare API token** — template "Edit zone DNS", permissions `Zone:DNS:Edit` + `Zone:Zone:Read`
- **SSH access** — key-based auth to all nodes (`task ansible:ssh:generate && task ansible:ssh:distribute`)

## Optional

- **NAS with SMB/CIFS** — for media storage (Synology, TrueNAS, OpenMediaVault — any works)
- **iSCSI target** — for database storage with OCFS2 cluster filesystem ([details](../architecture/storage.md))

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 2377 | TCP | Swarm management |
| 7946 | TCP/UDP | Container discovery |
| 4789 | UDP | Overlay network |
| 80/443 | TCP | HTTP/HTTPS (Traefik) |

See the [Quick Start](quick-start.md) for the full deployment walkthrough.
