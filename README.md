# Homelab

A Docker Swarm platform for self-hosted services. Deploys 37+ pre-configured services with automatic SSL, centralized SSO, monitoring, and automated backups.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)

---

## What's Included

**Infrastructure**
- Technitium DNS — primary local DNS with optional Pi-hole secondary for failover
- Traefik — reverse proxy with automatic SSL via Cloudflare
- Authentik — identity provider and SSO
- Prometheus + Grafana + Loki — metrics, dashboards, and log aggregation
- Uptime Kuma — uptime monitoring
- Kopia — encrypted backups to Backblaze B2

**Applications**
- Homepage, Actual Budget, Home Assistant, Node-RED, CryptPad, Mealie, Excalidraw, FreshRSS
- PhotoPrism, Immich, Emby, Komga (comics/manga)
- Sonarr, Radarr, Prowlarr, Profilarr, qBittorrent, Deluge, SABnzbd, NZBGet
- Forgejo (Git + CI/CD), GitHub Actions Runner, Code-server (VS Code in browser)
- Vaultwarden, LibreChat, Kiwix (offline Wikipedia + Stack Overflow)

---

## Requirements

- Ubuntu/Debian machine (control node — does not need to be a cluster node)
- Docker installed on each cluster node (handled by `task ansible:bootstrap`)
- Domain name with Cloudflare DNS management
- Cloudflare API token for DNS-01 challenge

---

## Quick Start

**1. Clone and bootstrap the control node**

```bash
git clone https://github.com/chutch3/homelab.git
cd homelab
bash setup.sh
```

`setup.sh` installs all required tools (`uv`, `task`, Node.js via fnm, Bitwarden CLI) and project dependencies. It is safe to re-run.

**2. Configure**

```bash
# Edit .env with your domain, Cloudflare token, and passwords
nano .env

# Add your cluster nodes
cp ansible/inventory/01-structure.yml ansible/inventory/02-hosts.yml
nano ansible/inventory/02-hosts.yml
```

**3. Deploy**

```bash
task ansible:ssh:generate    # create the homelab SSH key
task ansible:ssh:distribute  # push the key to your nodes
task ansible:bootstrap       # install Docker on all nodes
task ansible:cluster:init    # initialize Docker Swarm
task ansible:deploy          # deploy all services
```

Then visit `https://homepage.yourdomain.com`.

**Restore secrets from Bitwarden** (if you've used this repo before)

```bash
task ansible:secrets:login
task secrets:pull            # restores .env and ansible config from vault
```

---

## Common Commands

```bash
# Deploy or redeploy a single service
task ansible:deploy:stack -- -e "stack_name=sonarr"

# Tear down a service (preserves data)
task ansible:teardown:stack -- -e "stack_name=sonarr"

# Configure DNS records
task ansible:dns:configure

# Check cluster status
task ansible:cluster:status

# Run tests and linting
task check
```

---

## Documentation

Full documentation: [chutch3.github.io/homelab](https://chutch3.github.io/homelab/)

- [Getting Started](https://chutch3.github.io/homelab/getting-started/quick-start/)
- [Configuration](https://chutch3.github.io/homelab/getting-started/configuration/)
- [Architecture](https://chutch3.github.io/homelab/architecture/overview/)
- [Service Management](https://chutch3.github.io/homelab/user-guide/service-management/)
- [Troubleshooting](https://chutch3.github.io/homelab/troubleshooting/)

---

## License

MIT — see [LICENSE](LICENSE).
