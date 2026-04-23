# Homelab

A Docker Swarm platform for self-hosted services. Deploys 25+ pre-configured services with automatic SSL, centralized SSO, monitoring, and automated backups.

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
- Homepage, Actual Budget, Home Assistant, Node-RED, CryptPad, Mealie, Excalidraw
- PhotoPrism, Immich, Emby
- Sonarr, Radarr, Prowlarr, Profilarr, qBittorrent, Deluge, SABnzbd, NZBGet
- Vaultwarden, LibreChat, Kiwix (offline Wikipedia + Stack Overflow)

---

## Requirements

- Docker with Compose v2
- [Taskfile](https://taskfile.dev/installation/)
- Domain name with Cloudflare DNS management
- Cloudflare API token for DNS-01 challenge

---

## Quick Start

```bash
git clone https://github.com/chutch3/homelab.git
cd homelab

cp .env.example .env
nano .env  # set your domain, Cloudflare token, and passwords

cp ansible/inventory/03-hosts.yml.example ansible/inventory/02-hosts.yml
nano ansible/inventory/02-hosts.yml  # add your nodes
```

```bash
task ansible:install     # install Ansible and dependencies
task ansible:bootstrap   # install Docker on all nodes
task ansible:cluster:init  # initialize Docker Swarm
task ansible:deploy      # deploy all services
```

Then visit `https://homepage.yourdomain.com`.

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
