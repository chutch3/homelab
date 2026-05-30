# Prerequisites

## Control Node

The machine you run `bash setup.sh` and `task` commands from. Does not need to be a cluster node.

- **Ubuntu 22.04+ or Debian 11+**
- `bash setup.sh` installs everything else: `uv`, `task`, Node.js (via fnm), Bitwarden CLI, Ansible, and all project dependencies

## Cluster Nodes

The machines that actually run the services.

- **Ubuntu 22.04+ or Debian 11+**
- SSH access from the control node (`task ansible:ssh:distribute`)
- Docker is installed automatically by `task ansible:bootstrap` — no manual setup needed

## Cloudflare

- Domain name managed by Cloudflare
- Wildcard A record: `*` → your server IP (DNS-only / gray cloud)
- API token with `Zone:DNS:Edit` + `Zone:Zone:Read` permissions (use the "Edit zone DNS" template)

## Optional

- **NAS with SMB/CIFS** — for media storage (Synology, TrueNAS, OpenMediaVault)
- **iSCSI target** — for database storage with OCFS2 cluster filesystem ([details](../architecture/storage.md))

## Ports

Open these between cluster nodes:

| Port | Protocol | Purpose |
|------|----------|---------|
| 2377 | TCP | Swarm management |
| 7946 | TCP/UDP | Container discovery |
| 4789 | UDP | Overlay network |
| 80/443 | TCP | HTTP/HTTPS (Traefik) |

See the [Quick Start](quick-start.md) for the full deployment walkthrough.
