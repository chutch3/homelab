# Roadmap

Our mission is to create the ultimate self-hosting platform that makes running your own services as simple as possible while maintaining security, reliability, and flexibility.

!!! success "✅ **Production-Ready Platform Complete**"

    The core platform is fully functional with 25+ services, comprehensive testing, and CI/CD automation.

## Mission Statement

The mission of homelab is to:

- :material-server: **Use existing hardware** - Make the most of what you already have
- :material-rocket-launch: **Get up and running fast** - Deploy services in minutes, not hours
- :material-shield-check: **Enable data sovereignty and control** - Keep your data yours
- :material-tune: **Enable easy customization** - Adapt to your specific needs
- :material-link: **Connect open source projects together** - Unified ecosystem
- :material-apps: **Support multiple application domains** - Home automation, media, productivity, development, security
- :material-shield-half-full: **Build resilient systems** - Offline-first capabilities for network independence
- :material-book-open: **Documentation and guides** - Clear instructions for getting started

## 🔄 Current Status

### ✅ Completed Platform Features

<div class="grid cards" markdown>

- :material-cog: **Production-Ready Deployment**

    ---

    Docker Swarm with 25 pre-configured services ✅

- :material-shield-lock: **Automatic SSL & DNS**

    ---

    Traefik reverse proxy with Cloudflare integration ✅

- :material-chart-line: **Built-in Monitoring**

    ---

    Prometheus + Grafana for system observability ✅

- :material-console: **Simple Management CLI**

    ---

    Deploy, update, and manage services with one command ✅

- :material-test-tube: **Comprehensive Testing**

    ---

    Comprehensive test suite with CI/CD validation, TDD methodology ✅

- :material-github-action: **CI/CD Pipeline**

    ---

    GitHub Actions with automated testing, linting, semantic releases ✅

</div>

### ✅ Currently Deployed Services (25)

**Infrastructure & Networking:**
- :material-dns: **Technitium DNS** - Local DNS server ✅
- :material-shield-check: **Traefik** - Reverse proxy with automatic SSL ✅
- :material-chart-line: **Prometheus + Grafana** - System monitoring and dashboards ✅
- :material-monitor: **Node Exporter** - Host metrics collection ✅
- :material-docker: **cAdvisor** - Container-level performance metrics ✅
- :material-chart-box: **NVIDIA GPU Exporter** - GPU metrics and monitoring ✅
- :material-speedometer: **Speedtest Exporter** - Network speed monitoring ✅
- :material-network: **iperf3 Server + Exporter** - Network performance testing ✅
- :material-file-document-multiple: **Loki + Promtail** - Log aggregation and shipping ✅
- :material-heart-pulse: **Uptime Kuma** - Uptime monitoring with notifications ✅
- :material-account-key: **Authentik** - Identity provider and SSO (integrated with 8+ services) ✅

**Home & Productivity:**
- :material-view-dashboard: **Homepage** - Service dashboard ✅
- :material-cash: **Actual Budget** - Personal finance management ✅
- :material-home-automation: **Home Assistant** - Smart home automation platform ✅
- :material-sitemap: **Node-RED** - Flow-based automation for advanced smart home integration ✅
- :material-file-document: **CryptPad** - Collaborative documents with encryption ✅
- :material-food: **Mealie** - Recipe management and meal planning ✅

**Media & Photos:**
- :material-image: **PhotoPrism** - AI-powered photo management ✅
- :material-image-multiple: **Immich** - High-performance photo backup ✅
- :material-movie: **Emby** - Media server and streaming ✅

**Media Automation Stack:**
- :material-television: **Sonarr** - TV series management ✅
- :material-filmstrip: **Radarr** - Movie management ✅
- :material-video: **Whisparr** - Adult content management ✅
- :material-magnify: **Prowlarr** - Indexer management ✅
- :material-chart-box: **Profilarr** - Media quality profiling ✅
- :material-shield-search: **FlareSolverr** - Cloudflare bypass for indexers ✅
- :material-download: **qBittorrent** - Primary torrent client ✅
- :material-download: **Deluge** - Alternative torrent client ✅
- :material-download-box: **SABnzbd** - Usenet downloader ✅
- :material-download-box: **NZBGet** - Lightweight Usenet client ✅

**Prepper & Resilience:**
- :material-book-open-variant: **Kiwix** - Offline Wikipedia and knowledge archives ✅
  - Wikipedia (119GB with images)
  - Project Gutenberg (60,000+ ebooks)
  - WikiMed (medical encyclopedia)
  - Stack Overflow + Stack Exchange sites
  - WikiVoyage, OpenStreetMap Wiki
  - Gardening, DIY, Cooking, Sustainability knowledge

**Security & Privacy:**
- :material-lock: **Vaultwarden** - Bitwarden-compatible password manager (with Authentik SSO) ✅

**AI & Chat:**
- :material-robot: **LibreChat** - Self-hosted AI chat interface ✅

**Development & DevOps:**
- :material-brain: **MLflow** - ML experiment tracking, model registry, and serving ✅

**Backup & Recovery:**
- :material-backup-restore: **Kopia** - Automated encrypted backups to cloud storage (Backblaze B2) with web UI ✅
  - Backs up iSCSI-mounted application data weekly
  - Retention: 4 weekly + 3 monthly snapshots
  - Integrated with Authentik SSO

## 🚀 Future Services by Domain

### 🏠 Home & Lifestyle

| Service | Priority | Description |
|---------|----------|-------------|
| **Traccar** | Medium | GPS tracking for family safety and device location |
| **Grocy** | Medium | Groceries and household management |
| **Monica** | Low | Personal CRM and relationship management |
| **Paperless-ngx** | High | Document management and long-term archival system |

### 💼 Development & DevOps

**Note:** PostgreSQL and Redis are deployed with apps that need them (e.g., Immich includes PostgreSQL), not as standalone services.

| Service | Priority | Description |
|---------|----------|-------------|
| **Forgejo** | High | Self-hosted Git service with CI/CD (community-driven Gitea fork) |
| **Code-Server** | Medium | VS Code in the browser |
| **Harbor** | Low | Container registry and scanning |

### 📝 Productivity & Collaboration

| Service | Priority | Description |
|---------|----------|-------------|
| **NextCloud** | High | File sync, calendar, contacts, collaboration, long-term document storage |
| **Bookstack** | Medium | Wiki and documentation platform |
| **Memos** | Low | Lightweight note-taking |
| **Stirling-PDF** | Medium | PDF manipulation toolkit |

### 🔒 Security & Privacy

| Service | Priority | Description |
|---------|----------|-------------|
| **Searxng** | Medium | Private meta-search engine (aggregates results without tracking) |
| **AdGuard Home** | Medium | Network-wide ad and tracker blocking |
| **WireGuard** | High | VPN for secure remote access |
| **Crowdsec** | Low | Collaborative security engine |


### 🎯 Prepper & Resilience

*Building self-sufficient systems for network independence and long-term data preservation.*

**✅ Completed via Kiwix:**
- Wikipedia with images (offline encyclopedia)
- Project Gutenberg (60,000+ ebooks)
- WikiMed (medical knowledge)
- Stack Overflow + Stack Exchange (technical Q&A)
- WikiVoyage (travel guides)
- OpenStreetMap Wiki (mapping reference)
- Practical knowledge (gardening, DIY, cooking, sustainability)

**Future Services:**

| Service | Priority | Description | Status |
|---------|----------|-------------|--------|
| **Kolibri** | High | Offline educational platform with K-12 curriculum (Khan Academy, structured learning) | 🔄 Planned |
| **OpenStreetMap Tile Server** | High | Local map server for offline navigation with actual map tiles | 🔄 [Issue #13](https://github.com/chutch3/homelab/issues/13) |
| **Ollama** | High | Local LLM inference for offline AI assistance | 🔄 [Issue #13](https://github.com/chutch3/homelab/issues/13) |
| **Calibre-Web** | Medium | Ebook library management and reader (for managing additional ebook collections) | 🔄 Planned |
| **ArchiveBox** | Medium | Self-hosted web archive for important pages | 🔄 Planned |
| **FreshRSS** | Low | RSS reader for decentralized news aggregation | 🔄 Planned |

**Remaining Challenges ([Issue #13](https://github.com/chutch3/homelab/issues/13)):**
- ✅ ~~Source and licensing for offline data archives~~ (Solved via Kiwix ZIM files)
- ✅ ~~Automated init and update processes~~ (Implemented with monthly update checks)
- OpenStreetMap tile generation and storage strategy
- Source code archiving and mirror strategies
- Local LLM model management and updates

### 🎮 Gaming & Entertainment

| Service | Priority | Description |
|---------|----------|-------------|
| **Audiobookshelf** | Low | Audiobook and podcast server |
| **Navidrome** | Low | Music server and streamer |
| **Romm** | Low | ROM and game library management |

### 💾 Backup & Recovery

**Current:** Automated encrypted backups using Kopia to Backblaze B2 storage for iSCSI-mounted application data

| Service | Priority | Description | Status |
|---------|----------|-------------|--------|
| **Restic** | Low | Alternative encrypted backup tool (currently using Kopia) | 🔄 Alternative option |
| **Duplicati** | Low | Web-based backup with scheduling (simpler but less efficient) | 🔄 Alternative option |

### 🔧 Infrastructure & Monitoring

| Service | Priority | Description | Status |
|---------|----------|-------------|--------|
| ~~**Netdata**~~ | ~~Medium~~ | ~~Real-time performance monitoring~~ | ✅ **Alternative: Prometheus + Grafana + cAdvisor + Exporters** |
| ~~**Dozzle**~~ | ~~Low~~ | ~~Real-time log viewer~~ | ✅ **Alternative: Loki + Promtail + Grafana** |
| **Portainer** | Medium | Container management UI | 🔄 Planned (alternative to CLI) |
| **Watchtower** | Low | Automated container updates | 🔄 Planned |

[View complete roadmap →](https://github.com/chutch3/homelab/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

## 🤝 How to Contribute

We welcome contributions! Here's how you can help:

<div class="grid cards" markdown>

- :material-plus-circle: **Add New Services**

    ---

    Contribute service definitions for popular applications

- :material-test-tube: **Improve Testing**

    ---

    Help us achieve 100% test coverage

- :material-book-open: **Write Documentation**

    ---

    Help other users get started faster

- :material-bug: **Report Bugs**

    ---

    Help us identify and fix issues

</div>

### Current Contribution Opportunities

**🔥 Hot Topics** (Help Wanted):

1. **Prepper Services** - OpenStreetMap tile server, local LLM hosting (Ollama), web archiving (ArchiveBox)
2. **Security & Privacy** - WireGuard VPN, AdGuard Home, expanding Authentik SSO to more services
3. **Development Tools** - Forgejo with CI/CD, code editing tools
4. **Productivity Suite** - NextCloud deployment, Paperless-ngx document management
5. **Infrastructure** - Portainer container management (monitoring is complete)
6. **Documentation** - Service setup guides, domain-specific tutorials, Authentik SSO integration guide
7. **Testing** - Integration tests for new services
8. **Storage** - Expanding iSCSI storage strategy for more services

**Domain-Specific Needs:**

- **Prepper/Resilience**: OpenStreetMap tile generation, LLM model management, source code archiving
- **Home Automation**: Advanced Node-RED flows, Home Assistant integrations
- **Media**: Alternative servers (Jellyfin), codec optimization, iSCSI storage expansion
- **Security**: Expanding Authentik SSO integrations, network security hardening, VPN access
- **Backup & Recovery**: Expanding Kopia coverage to additional data sources

[Get started contributing →](https://github.com/chutch3/homelab/issues)

## 💡 Have Ideas?

Share your suggestions:

- **Feature Requests**: [Open an issue](https://github.com/chutch3/homelab/issues/new)
- **Discussions**: [Join our discussions](https://github.com/chutch3/homelab/discussions)
- **Community**: [r/selfhosted](https://reddit.com/r/selfhosted)

Together, we're building the future of self-hosting! 🚀
