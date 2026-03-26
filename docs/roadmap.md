# 🛣️ The Homelab Journey

*A vertical road map of our self-hosting adventure*

---

```
                    🏁 STARTING LINE 🏁
                         ║
                         ║
```

## 🎯 Mission: The Destination Ahead

Our mission is to create the ultimate self-hosting platform that makes running your own services as simple as possible while maintaining security, reliability, and flexibility.

**Why This Journey?**

- 🖥️ **Use existing hardware** - Make the most of what you already have
- 🚀 **Get up and running fast** - Deploy services in minutes, not hours
- 🔐 **Enable data sovereignty and control** - Keep your data yours
- ⚙️ **Enable easy customization** - Adapt to your specific needs
- 🔗 **Connect open source projects together** - Unified ecosystem
- 📱 **Support multiple application domains** - Home automation, media, productivity, development, security
- 🛡️ **Build resilient systems** - Offline-first capabilities for network independence
- 📚 **Documentation and guides** - Clear instructions for getting started

---

```
                         ║
                         ║
                    ╔════╩════╗
                    ║  MILE   ║
                    ║    1    ║
                    ╚════╦════╝
                         ║
```

## ✅ MILE 1: Foundation & Infrastructure
**Status:** COMPLETED • **Date:** 2024-Q4

<div class="grid cards" markdown>

- 🐳 **Docker Swarm Deployment**

    ---

    Production-ready orchestration with 25+ services

- 🔒 **Automatic SSL & DNS**

    ---

    Traefik reverse proxy + Cloudflare integration

- 📊 **Monitoring Stack**

    ---

    Prometheus + Grafana + Loki for full observability

- 🔧 **Management CLI**

    ---

    Deploy and manage services with one command

</div>

**Rest Stop Summary:** Core platform infrastructure complete ✅

---

```
                         ║
                    - - -║- - -
                    - - -║- - -
                         ║
                    ╔════╩════╗
                    ║  MILE   ║
                    ║    2    ║
                    ╚════╦════╝
                         ║
```

## ✅ MILE 2: Essential Services (27 Deployed)
**Status:** COMPLETED • **Services Live:** 27

### 🏗️ Infrastructure Layer
- ✅ Technitium DNS - Local DNS server
- ✅ Traefik - Reverse proxy with automatic SSL
- ✅ Prometheus + Grafana - Metrics and dashboards
- ✅ Node Exporter - Host metrics collection
- ✅ cAdvisor - Container-level performance metrics
- ✅ NVIDIA GPU Exporter - GPU metrics and monitoring
- ✅ Speedtest Exporter - Network speed monitoring
- ✅ iperf3 Server + Exporter - Network performance testing
- ✅ Loki + Promtail - Log aggregation
- ✅ Uptime Kuma - Uptime monitoring
- ✅ Authentik - SSO (integrated with 8+ services)

### 🏠 Home & Productivity
- ✅ Homepage - Service dashboard
- ✅ Actual Budget - Personal finance
- ✅ Home Assistant + Node-RED - Smart home platform
- ✅ CryptPad - Encrypted collaboration
- ✅ Mealie - Recipe management

### 📷 Media & Photos
- ✅ PhotoPrism - AI-powered photo management
- ✅ Immich - High-performance photo backup
- ✅ Emby - Media streaming

### 🎬 Media Automation (The *arr Stack)
- ✅ Sonarr + Radarr + Whisparr + Prowlarr + Profilarr
- ✅ FlareSolverr - Cloudflare bypass for indexers
- ✅ qBittorrent + Deluge - Torrent clients
- ✅ SABnzbd + NZBGet - Usenet clients

### 🛡️ Prepper & Resilience
- ✅ Kiwix - Offline Wikipedia (119GB) + Project Gutenberg + Stack Overflow + Medical knowledge
- ✅ Kolibri - Offline K-12 educational platform (Khan Academy, CK-12, and more)

### 🔐 Security & Privacy
- ✅ Vaultwarden - Password manager (with Authentik SSO)

### 🤖 AI & Development
- ✅ LibreChat - AI chat interface
- ✅ MLflow - ML experiment tracking
- ✅ Forgejo - Self-hosted Git service with issue tracking and CI/CD

### 💾 Backup & Recovery
- ✅ Kopia - Automated encrypted backups to Backblaze B2

**Rest Stop Summary:** Production platform with 27 services ✅

---

```
                         ║
                    - - -║- - -
                    - - -║- - -
                         ║
                    ╔════╩════╗
                    ║  MILE   ║
                    ║    3    ║
                    ╚════╦════╝
                         ║
```

## ✅ MILE 3: Quality & Automation
**Status:** COMPLETED • **Date:** 2024-Q4

- ✅ Comprehensive test suite with TDD methodology
- ✅ GitHub Actions CI/CD pipeline
- ✅ Automated testing, linting, and validation
- ✅ Semantic versioning and releases

**Rest Stop Summary:** Professional-grade development workflow ✅

---

```
                         ║
                    = = =║= = =  🚗 YOU ARE HERE
                    = = =║= = =
                         ║
                    ╔════╩════╗
                    ║ CURRENT ║
                    ║ LOCATION║
                    ╚════╦════╝
                         ║
```

## 🚗 Current Location: Maintenance & Documentation
**Status:** IN PROGRESS

- 🔄 Keeping services updated and healthy
- 📚 Improving documentation
- 🧪 Expanding test coverage
- 🔍 Planning next destinations

---

```
                         ║
                    - - -║- - -
                    - - -║- - -
                         ║
                    🚧   ║   🚧
                    ╔════╩════╗
                    ║  NEXT   ║
                    ║   EXIT  ║
                    ╚════╦════╝
                         ║
```

## 🗺️ The Road Ahead: Future Destinations

### ✅ Recently Completed

| Service | Details |
|---------|---------|
| **Forgejo** | Self-hosted Git service with PostgreSQL backend, Authentik OIDC SSO, SSH access on port 2222, and iSCSI storage. Deployed at `git.yourdomain.com` |
| **CI/CD Runners** | Dual runner setup: **Forgejo Runner** for local Git projects and **GitHub Runner** for building/testing GitHub.com repositories on homelab hardware. |
| **Kolibri** | Offline K-12 educational platform with Khan Academy content, hybrid iSCSI + CIFS storage, optional Authentik OIDC. Deployed at `kolibri.yourdomain.com` |

### 🎯 NEEDS (High Priority - Real Gaps to Fill)

| Need / Current Gap | Solution | Why It Matters |
|-------------------|----------|----------------|
| **Document Management & Archival**<br>No system for organizing scanned documents, PDFs, receipts, tax forms, contracts | **Paperless-ngx** | Long-term archival with OCR, tagging, full-text search, automated organization |
| **File Sync, Calendar, & Contacts**<br>No unified cloud storage replacement or calendar/contacts synchronization | **NextCloud** | Self-hosted file sync across devices, calendar management, contacts storage, document collaboration |
| **Offline AI Assistance**<br>LibreChat requires external API calls - no true offline AI capability | **Ollama**<br>(integrates with LibreChat) | Run LLMs locally for offline AI assistance, privacy, no API costs |
| **Offline Navigation Maps**<br>Kiwix has OSM Wiki documentation but not actual map tiles for GPS navigation | **OpenStreetMap Tile Server** | Render and serve map tiles locally for offline navigation and mapping apps |
| **Web Page Archiving**<br>No way to preserve important websites before they disappear or change | **ArchiveBox** | Archive critical web pages, articles, and sites for offline reference and preservation |

---

### 💭 NICE TO HAVE (Lower Priority - Potential Future Needs)

| Possible Need / Gap | Solution | Why It Matters |
|-------------------|----------|----------------|
| **Private Search Engine**<br>Reliance on external search engines that track queries | **Searxng** | Meta-search engine that aggregates results without tracking or profiling |
| **Family GPS Tracking**<br>No way to locate family members or track device locations for safety | **Traccar** | Real-time GPS tracking, geofencing, location history |
| **Pantry & Grocery Inventory**<br>Mealie handles recipes but not pantry inventory, expiration tracking, shopping lists | **Grocy** | Track groceries, expiration dates, automate shopping lists, reduce food waste |
| **Ebook Library Management**<br>Kiwix has Project Gutenberg but no management for personal ebook collections | **Calibre-Web** | Organize, tag, and read personal ebook collections with web interface |
| **Knowledge Base / Wiki**<br>CryptPad handles collaboration but not structured wiki documentation | **Bookstack** | Organized wiki with books, chapters, pages for structured documentation |
| **PDF Manipulation**<br>No self-hosted tools for merging, splitting, converting, or editing PDFs | **Stirling-PDF** | Comprehensive PDF toolkit for all manipulation tasks |
| **Personal CRM**<br>No system for tracking relationships, interactions, and personal contacts | **Monica** | Remember important dates, track conversations, manage personal relationships |
| **RSS Feed Aggregation**<br>No centralized way to follow blogs, news, and content without algorithms | **FreshRSS** | Decentralized news reading, control your feed, offline reading |
| **Container Registry**<br>No private registry for custom Docker images | **Harbor** | Store and scan custom container images, vulnerability scanning |
| **Web-based IDE**<br>No browser-based code editing environment | **Code-Server**<br>(VS Code in browser) | Code from any device, remote development environment |
| **Collaborative Security**<br>No crowdsourced threat intelligence or IP reputation | **Crowdsec** | Block IPs based on community threat intelligence |
| **ROM & Game Library**<br>No management system for retro game ROMs | **Romm** | Organize and manage retro gaming library |
| **Automated Container Updates**<br>Manual service updates required | **Watchtower** | Automatically pull and update container images |
