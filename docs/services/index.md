# Services

**41 deployed** · **15 SSO-integrated** · **v3.14.0**

Deploy any service: `task ansible:deploy:stack -- -e "stack_name=<name>"`

---

## Identity & Security

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Authentik](authentik.md) | `auth.*` | `authentik` | SSO provider — OIDC, LDAP, forward auth for 15 services |
| [Vaultwarden](vaultwarden.md) | `vaultwarden.*` | `vaultwarden` | Bitwarden-compatible password manager with SSO |

---

## Infrastructure & Monitoring

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Kopia](kopia.md) | `backup.*` | `kopia` | Encrypted backups to Backblaze B2 |
| [Uptime Kuma](uptime-kuma.md) | `uptime.*` | `uptime-kuma` | HTTP/TCP/ping monitoring with status pages |
| [LibreNMS](librenms.md) | `librenms.*` | `librenms` | Network discovery, SNMP polling, syslog, traps |
| [Cert-sync-nas](cert-sync-nas.md) | internal | `cert-sync-nas` | Wildcard SSL sync to NAS via SSH |

---

## Finance

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Actual Budget](actual_server.md) | `budget.*` | `actual_server` | Zero-based budgeting with bank sync |

---

## Media Management

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [PhotoPrism](photoprism.md) | `photos.*` | `photoprism` | AI-powered photo tagging and organization |
| [Takeout Manager](takeout-manager.md) | `takeout.*` | `takeout-manager` | Google Photos Takeout distributed downloads |
| [Immich](immich.md) | `photos.*` | `immich` | Mobile-first photo backup with ML |
| [Emby](emby.md) | `emby.*` | `emby` | Media streaming — movies, TV, music |

---

## Media Automation

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Sonarr](sonarr.md) | `sonarr.*` | `sonarr` | Automated TV show management |
| [Radarr](radarr.md) | `radarr.*` | `radarr` | Automated movie management |
| [Whisparr](whisparr.md) | `whisparr.*` | `whisparr` | Automated adult content management |
| [Prowlarr](prowlarr.md) | `prowlarr.*` | `prowlarr` | Indexer manager for all arr services |
| [Profilarr](profilarr.md) | `profilarr.*` | `profilarr` | Quality profile sync across arr services |
| [FlareSolverr](flaresolverr.md) | internal | `flaresolverr` | Cloudflare bypass proxy for indexers |

---

## Download Clients

All clients route through NordVPN (OpenVPN). VPN kill switch active.

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Downloads Stack](downloads.md) | — | `downloads` | Unified VPN + 4 clients below |
| qBittorrent | `qbittorrent.*` | ↑ | Primary torrent client |
| Deluge | `deluge.*` | ↑ | Alternative torrent client |
| SABnzbd | `sabnzbd.*` | ↑ | Primary usenet downloader |
| NZBGet | `nzbget.*` | ↑ | Lightweight usenet alternative |

---

## Productivity & Collaboration

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [CryptPad](cryptpad.md) | `cryptpad.*` | `cryptpad` | E2E encrypted docs, sheets, kanban |
| [Mealie](mealie.md) | `mealie.*` | `mealie` | Recipe management and meal planning |
| [FreshRSS](freshrss.md) | `rss.*` | `freshrss` | RSS/Atom feed aggregator |
| [draw.io](drawio.md) | `draw.*` | `drawio` | Network and architecture diagramming |

---

## Home Automation

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Home Assistant](homeassistant.md) | `home.*` | `homeassistant` | Smart home control — 2000+ integrations |
| [Node-RED](node-red.md) | `nodered.*` | `node-red` | Visual flow-based automation |

---

## AI & Chat

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Ollama](ollama.md) | `ollama.*` | `ollama` | Local LLM inference with GPU |
| [LibreChat](librechat.md) | `chat.*` | `librechat` | Multi-model AI chat (GPT, Claude, local) |

---

## Development & ML

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [MLflow](mlflow.md) | `mlflow.*` | `mlflow` | ML experiment tracking and model registry |
| [Prefect](prefect.md) | `prefect.*` | `prefect` | Python workflow orchestration |

---

## Development & CI/CD

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Forgejo](forgejo.md) | `git.*` | `forgejo` | Git hosting with issues, PRs, wiki |
| [CI/CD Runner](cicd.md) | `cicd.*` | `cicd` | Forgejo Actions runner |
| [GitHub Runner](github-runner.md) | — | `github-runner` | Self-hosted GitHub Actions runner |
| [Code-server](code-server.md) | `code.*` | `code-server` | VS Code in the browser |
| [ClaudeCodeUI](claudecodeui.md) | `ai.*` | `claudecodeui` | Browser-based Claude Code |

---

## Knowledge & Learning

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Kiwix](kiwix.md) | `kiwix.*` | `kiwix` | Offline Wikipedia, Stack Overflow, medical |
| [Kolibri](kolibri.md) | `kolibri.*` | `kolibri` | Offline K-12 education (Khan Academy) |
| [Komga](komga.md) | `komga.*` | `komga` | Comics and manga library |

---

## Privacy & Anonymity

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Tor Browser](tor-browser.md) | `tor.*` | `tor-browser` | KasmVNC + WireGuard VPN with kill switch |

---

## Core Infrastructure

| Service | Domain | Stack Name | Notes |
|---------|--------|------------|-------|
| [Homepage](homepage.md) | `dashboard.*` | `homepage` | Service dashboard with widgets |

---

## Infrastructure Stacks

| Stack | Purpose |
|-------|---------|
| [reverse-proxy](reverse-proxy.md) | Traefik + automatic SSL |
| [dns](dns.md) | Technitium DNS server |
| [monitoring](monitoring.md) | Prometheus + Grafana + Loki + Promtail |

---

## Adding a New Service

```bash
mkdir stacks/apps/myservice
```

```yaml
# stacks/apps/myservice/docker-compose.yml
services:
  myservice:
    image: myapp:latest
    networks:
      - traefik-public
    deploy:
      labels:
        - traefik.enable=true
        - traefik.http.routers.myservice.rule=Host(`myapp.${BASE_DOMAIN}`)
        - traefik.http.routers.myservice.tls.certresolver=dns
        - traefik.http.services.myservice.loadbalancer.server.port=3000
        - traefik.swarm.network=traefik-public

networks:
  traefik-public:
    external: true
```

```bash
task ansible:deploy:stack -- -e "stack_name=myservice"
```
