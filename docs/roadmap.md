# Roadmap

## Current — v3.14.0

Operations hardening and platform expansion.

- Cluster observability — Grafana health dashboard, health check script
- Safe single-node reboot playbook (drain → unmount → reboot → reconnect → redeploy)
- DNS pluggable adapter pattern (primary/secondary decoupled)
- SNMP monitoring role with LibreNMS integration
- Hardened Bitwarden secrets adapter
- Test coverage expansion (unit + integration split)

---

## Completed

### v3.14.0 — Platform Expansion

| What | Details |
|------|---------|
| LibreNMS | Network monitoring — SNMP, syslog, traps, distributed polling |
| draw.io | Stateless diagramming tool |
| Tor Browser | KasmVNC + WireGuard VPN with kill switch |
| SNMP role | Ansible role for node monitoring with Bitwarden sync |

### v3.12.0 — Services & CI/CD

| What | Details |
|------|---------|
| Forgejo | Self-hosted Git with PostgreSQL, OIDC SSO, SSH |
| CI/CD Runners | Forgejo runner + GitHub runner on homelab hardware |
| Prefect | Python workflow orchestration for data/ML pipelines |
| Kolibri | Offline K-12 education (Khan Academy, CK-12) |
| Ollama | Local LLM inference integrated with LibreChat |
| Excalidraw | Collaborative whiteboard with real-time rooms |
| FreshRSS | RSS aggregator with Authentik SSO |
| Komga + Tranga | Manga library with automated MangaDex downloads |
| Newtarr | Unified arr services portal |
| Cluster health | Grafana dashboard + shell health check + reboot playbook |

### Foundation (2024-Q4)

| Milestone | What shipped |
|-----------|-------------|
| Infrastructure | Docker Swarm, Traefik SSL, Technitium DNS, monitoring stack |
| 41 services | Media, AI, finance, home automation, privacy, education, dev tools |
| Quality | TDD test suite, GitHub Actions CI/CD, semantic versioning |

---

## Planned

### High Priority

| Gap | Solution | Why |
|-----|----------|-----|
| Document management | Paperless-ngx | OCR, tagging, full-text search for PDFs/receipts/contracts |
| File sync + calendar | NextCloud | Cloud storage replacement, calendar, contacts |
| Offline maps | OpenStreetMap tile server | Local map tiles for GPS navigation |
| Web archiving | ArchiveBox | Preserve important web pages before they disappear |

### Backlog

| Solution | Purpose |
|----------|---------|
| SearXNG | Private meta-search engine |
| Traccar | Family GPS tracking and geofencing |
| Grocy | Pantry inventory and grocery management |
| Calibre-Web | Personal ebook library |
| Bookstack | Structured wiki/knowledge base |
| Stirling-PDF | PDF merge, split, convert toolkit |
| Monica | Personal CRM and relationship tracking |
| Harbor | Private container registry with scanning |
| CrowdSec | Crowdsourced IP reputation and blocking |
| Romm | Retro game ROM management |
| Watchtower | Automated container image updates |
