# Roadmap

Our mission is to create the ultimate self-hosting platform that makes running your own services as simple as possible while maintaining security, reliability, and flexibility.

!!! success "✅ **Production-Ready Platform Complete**"

    The core platform is fully functional with comprehensive testing and CI/CD automation.

## Mission Statement

The mission of selfhosted is to:

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

    Docker Swarm with 13+ pre-configured services ✅

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

    152 tests with 95%+ pass rate, TDD methodology ✅

- :material-github-action: **CI/CD Pipeline**

    ---

    GitHub Actions with automated testing, linting, semantic releases ✅

</div>

### ✅ Currently Deployed Services (13+)

**Infrastructure & Networking:**
- :material-dns: **Technitium DNS** - Local DNS server ✅
- :material-shield-check: **Traefik** - Reverse proxy with automatic SSL ✅
- :material-chart-line: **Prometheus + Grafana** - System monitoring and dashboards ✅

**Home & Productivity:**
- :material-view-dashboard: **Homepage** - Service dashboard ✅
- :material-cash: **Actual Budget** - Personal finance management ✅
- :material-home-automation: **Home Assistant** - Smart home automation platform ✅
- :material-file-document: **CryptPad** - Collaborative documents with encryption ✅

**Media & Photos:**
- :material-image: **PhotoPrism** - AI-powered photo management ✅
- :material-movie: **Emby** - Media server and streaming ✅

**Media Automation Stack:**
- :material-television: **Sonarr** - TV series management ✅
- :material-filmstrip: **Radarr** - Movie management ✅
- :material-magnify: **Prowlarr** - Indexer management ✅
- :material-download: **qBittorrent** - Primary torrent client ✅
- :material-download: **Deluge** - Alternative torrent client ✅

**AI & Chat:**
- :material-robot: **LibreChat** - Self-hosted AI chat interface ✅

## 🚀 Future Services by Domain

### 🏠 Home & Lifestyle

| Service | Priority | Description |
|---------|----------|-------------|
| **Node-RED** | High | Flow-based automation for advanced smart home integration |
| **Grocy** | Medium | Groceries and household management |
| **Mealie** | Medium | Recipe management and meal planning |
| **Monica** | Low | Personal CRM and relationship management |
| **Paperless-ngx** | High | Document management system |

### 💼 Development & DevOps

| Service | Priority | Description |
|---------|----------|-------------|
| **Gitea** | High | Self-hosted Git service with CI/CD |
| **Forgejo** | Medium | Community-driven Gitea fork |
| **Code-Server** | Medium | VS Code in the browser |
| **PostgreSQL** | High | Relational database for apps |
| **Redis** | High | In-memory cache and message broker |
| **Harbor** | Low | Container registry and scanning |

### 📝 Productivity & Collaboration

| Service | Priority | Description |
|---------|----------|-------------|
| **NextCloud** | High | File sync, calendar, contacts, collaboration |
| **Bookstack** | Medium | Wiki and documentation platform |
| **Outline** | Medium | Knowledge base and team wiki |
| **Memos** | Low | Lightweight note-taking |
| **Stirling-PDF** | Medium | PDF manipulation toolkit |

### 🔒 Security & Privacy

| Service | Priority | Description |
|---------|----------|-------------|
| **Vaultwarden** | High | Bitwarden-compatible password manager |
| **Authentik** | Medium | Identity provider and SSO |
| **AdGuard Home** | Medium | Network-wide ad and tracker blocking |
| **WireGuard** | High | VPN for secure remote access |
| **Crowdsec** | Low | Collaborative security engine |

### 📬 Communication

| Service | Priority | Description |
|---------|----------|-------------|
| **Matrix (Synapse)** | Medium | Federated chat and messaging |
| **Mailu** | Low | Complete email server suite |
| **Jitsi Meet** | Low | Video conferencing platform |
| **Mailcow** | Low | Email server with web UI |

### 🎯 Prepper & Resilience

*Building self-sufficient systems for network independence and long-term data preservation.*

| Service | Priority | Description | Status |
|---------|----------|-------------|--------|
| **Kiwix** | High | Offline Wikipedia, Stack Exchange, medical guides | 🔄 [Issue #13](https://github.com/chutch3/selfhosted.sh/issues/13) |
| **OpenStreetMap Tile Server** | High | Local map server for offline navigation | 🔄 [Issue #13](https://github.com/chutch3/selfhosted.sh/issues/13) |
| **Ollama** | High | Local LLM inference for offline AI assistance | 🔄 [Issue #13](https://github.com/chutch3/selfhosted.sh/issues/13) |
| **LocalAI** | Medium | Alternative local AI inference platform | 🔄 Planned |
| **Calibre-Web** | Medium | Ebook library management and reader | 🔄 Planned |
| **Project Gutenberg Mirror** | Low | 70,000+ free ebooks for offline access | 🔄 Planned |
| **ArchiveBox** | Medium | Self-hosted web archive for important pages | 🔄 Planned |
| **FreshRSS** | Low | RSS reader for decentralized news aggregation | 🔄 Planned |

**Key Questions for Prepper Services ([Issue #13](https://github.com/chutch3/selfhosted.sh/issues/13)):**
- Source and licensing for offline data archives
- Automated init and update processes for large datasets
- Storage strategy for knowledge vs personal backups
- Source code archiving and mirror strategies

### 🎮 Gaming & Entertainment

| Service | Priority | Description |
|---------|----------|-------------|
| **Jellyfin** | Medium | Alternative media server (FOSS alternative to Emby) |
| **Immich** | Medium | High-performance photo backup (alternative to PhotoPrism) |
| **Audiobookshelf** | Low | Audiobook and podcast server |
| **Navidrome** | Low | Music server and streamer |
| **Romm** | Low | ROM and game library management |

### 🔧 Infrastructure & Monitoring

| Service | Priority | Description |
|---------|----------|-------------|
| **Uptime Kuma** | High | Uptime monitoring with notifications |
| **Netdata** | Medium | Real-time performance monitoring |
| **Portainer** | Medium | Container management UI |
| **Dozzle** | Low | Real-time log viewer for Docker |
| **Watchtower** | Low | Automated container updates |

[View complete roadmap →](https://github.com/chutch3/selfhosted.sh/issues?q=is%3Aissue+is%3Aopen+label%3Aenhancement)

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

1. **Prepper Services** - Implement offline Wikipedia (Kiwix), OpenStreetMap tile server, local LLM hosting
2. **Security & Privacy** - Vaultwarden password manager, WireGuard VPN, Authentik SSO
3. **Development Tools** - Gitea/Forgejo, PostgreSQL, Redis integration
4. **Productivity Suite** - NextCloud deployment, Paperless-ngx document management
5. **Infrastructure** - Uptime Kuma monitoring, Portainer container management
6. **Documentation** - Service setup guides, domain-specific tutorials
7. **Testing** - Integration tests for new services

**Domain-Specific Needs:**

- **Prepper/Resilience**: Data archiving strategies, update automation, storage optimization
- **Home Automation**: Advanced Node-RED flows, Home Assistant integrations
- **Media**: Alternative servers (Jellyfin, Immich), codec optimization
- **Security**: SSO implementation, network security hardening

[Get started contributing →](https://github.com/chutch3/selfhosted.sh/issues)

## 💡 Have Ideas?

Share your suggestions:

- **Feature Requests**: [Open an issue](https://github.com/chutch3/selfhosted.sh/issues/new)
- **Discussions**: [Join our discussions](https://github.com/chutch3/selfhosted.sh/discussions)
- **Community**: [r/selfhosted](https://reddit.com/r/selfhosted)

Together, we're building the future of self-hosting! 🚀
