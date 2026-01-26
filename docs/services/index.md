# Available Services

Browse our comprehensive catalog of self-hosted services. Each service is pre-configured and ready to deploy with a single command.

## Service Categories

<div class="grid cards" markdown>

- :material-shield-account: **[Identity & Security](#identity-security)**

    ---

    Authentication, SSO, and password management

    **2 services available**

- :material-server-network: **[Infrastructure & Monitoring](#infrastructure-monitoring)**

    ---

    Backups, monitoring, and certificate management

    **3 services available**

- :material-chart-line: **[Finance & Budgeting](#finance-budgeting)**

    ---

    Manage your personal finances and track expenses

    **1 service available**

- :material-image: **[Media Management](#media-management)**

    ---

    Organize and stream your photos, videos, and music

    **4 services available**

- :material-download: **[Media Automation](#media-automation)**

    ---

    Automated media discovery and acquisition

    **6 services available**

- :material-cloud-download: **[Download Clients](#download-clients)**

    ---

    Torrent and Usenet download clients with VPN

    **4 clients + VPN in unified stack**

- :material-file-document: **[Productivity & Collaboration](#productivity-collaboration)**

    ---

    Document editing, recipes, and team collaboration

    **2 services available**

- :material-home-automation: **[Home Automation](#home-automation)**

    ---

    Automate your home with open-source solutions

    **2 services available**

- :material-robot: **[AI & Chat](#ai-chat)**

    ---

    Self-hosted AI chat interfaces

    **1 service available**

- :material-brain: **[Development & ML](#development-ml)**

    ---

    Machine learning experiment tracking

    **1 service available**

- :material-book-open-variant: **[Knowledge & Learning](#knowledge-learning)**

    ---

    Offline knowledge bases and reference materials

    **1 service available**

- :material-view-dashboard: **[Core Infrastructure](#core-infrastructure)**

    ---

    Essential dashboard for your homelab

    **1 service available**

</div>

---

## Identity & Security

### Authentik {#authentik}

<div class="service-card">

**Enterprise-grade identity provider and SSO platform**

- **Domain**: `auth.yourdomain.com`
- **Port**: `9000`
- **Status**: ✅ Available
- **Tags**: `security` `sso` `identity` `ldap` `oauth`

#### Features
- OpenID Connect (OIDC) provider for modern SSO
- LDAP interface for legacy application support
- Forward auth middleware for Traefik-protected services
- Multi-factor authentication (MFA)
- User self-service portal
- Custom branding and templates
- Policy-based access control

#### SSO Integration
Authentik is the central SSO provider for the homelab. **8+ services integrated**:
- **OAuth/OIDC**: Vaultwarden, Immich, Mealie
- **Forward Auth**: Kopia, Node-RED, qBittorrent, Deluge, SABnzbd, NZBGet
- **LDAP**: Emby

#### Prerequisites
- PostgreSQL 16 (auto-configured)
- Redis (auto-configured)
- iSCSI storage for application data

#### Storage Requirements
- Database: ~500MB growing over time
- Media/templates: ~100MB

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=authentik"
```

[Learn more about Authentik →](https://goauthentik.io/)

</div>

### Vaultwarden {#vaultwarden}

<div class="service-card">

**Bitwarden-compatible password manager**

- **Domain**: `vaultwarden.yourdomain.com`
- **Port**: `80`
- **Status**: ✅ Available
- **Tags**: `security` `passwords` `privacy` `sso`

#### Features
- Full Bitwarden compatibility
- Browser extensions and mobile apps
- Password generator
- Secure sharing
- Two-factor authentication
- Admin dashboard

#### Authentik SSO Integration
- **Method**: OAuth/OIDC
- Auto-registration enabled
- Fallback to native authentication available

#### Prerequisites
- Authentik SSO configured
- iSCSI storage for vault data

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=vaultwarden"
```

[Learn more about Vaultwarden →](https://github.com/dani-garcia/vaultwarden)

</div>

---

## Infrastructure & Monitoring

### Kopia {#kopia}

<div class="service-card">

**Fast and secure encrypted backup system**

- **Domain**: `backup.yourdomain.com`
- **Port**: `51515`
- **Status**: ✅ Available
- **Tags**: `backup` `encryption` `infrastructure` `sso`

#### Features
- Deduplication and compression
- Encrypted at rest
- Cloud storage backends (B2, S3, etc.)
- Web UI for management
- Snapshot retention policies
- Incremental backups
- Cross-platform support

#### Authentik SSO Integration
- **Method**: Forward Auth Middleware
- Basic credentials still required for API/CLI access

#### Backup Configuration
- **Source**: `/mnt/iscsi/app-data` and `/mnt/iscsi/media-apps`
- **Schedule**: Weekly backups
- **Retention**: 4 weekly + 3 monthly snapshots
- **Backend**: Backblaze B2 storage

#### Prerequisites
- Backblaze B2 account (or compatible S3 storage)
- iSCSI storage mounted

#### Storage Requirements
- Config: ~50MB
- Cache: Growing based on backup size

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=kopia"
```

[Learn more about Kopia →](https://kopia.io/)

</div>

### Uptime Kuma {#uptime-kuma}

<div class="service-card">

**Self-hosted uptime monitoring and status page**

- **Domain**: `uptime.yourdomain.com`
- **Port**: `3001`
- **Status**: ✅ Available
- **Tags**: `monitoring` `uptime` `notifications`

#### Features
- HTTP(S), TCP, ping, and DNS monitoring
- Beautiful status pages
- Multiple notification channels (email, Slack, Discord, etc.)
- Multi-language support
- Certificate expiry monitoring
- Incident timeline
- 20+ notification types

#### Prerequisites
- iSCSI storage for database

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=uptime-kuma"
```

[Learn more about Uptime Kuma →](https://uptime.kuma.pet/)

</div>

### Cert-sync-nas {#cert-sync-nas}

<div class="service-card">

**Automatic SSL certificate synchronization to NAS**

- **Domain**: Internal service (not exposed)
- **Port**: N/A
- **Status**: ✅ Available
- **Tags**: `infrastructure` `ssl` `automation` `internal`

#### Features
- Automatic wildcard certificate extraction from Traefik
- SSH-based sync to OpenMediaVault NAS
- Cloudflare DNS-01 challenge support
- Weekly automated renewal (Sundays 3 AM)
- OpenMediaVault API integration

#### Functionality
1. Extracts wildcard certificate from Traefik's acme.json
2. Copies certificate to NAS via SSH
3. Installs certificate in OpenMediaVault via RPC
4. Runs on deployment + weekly schedule

#### Prerequisites
- Traefik with Cloudflare DNS challenge
- OpenMediaVault NAS with SSH access
- SSH key configured

This service is primarily internal and requires no user interaction after initial setup.

</div>

---

## Finance & Budgeting

### Actual Budget {#actual-budget}

<div class="service-card">

**Personal finance and budgeting application**

- **Domain**: `budget.yourdomain.com`
- **Port**: `5006`
- **Status**: ✅ Available
- **Tags**: `finance` `budgeting` `privacy`

#### Features
- Zero-based budgeting
- Bank synchronization
- Multi-device sync
- Completely private and self-hosted
- Clean, intuitive interface
- Budget templates
- Detailed reports

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=actual_server"
```

[Learn more about Actual Budget →](https://actualbudget.org/)

</div>

---

## Media Management

### PhotoPrism {#photoprism}

<div class="service-card">

**AI-powered photo management and organization**

- **Domain**: `photos.yourdomain.com`
- **Port**: `2342`
- **Status**: ✅ Available
- **Tags**: `media` `photos` `ai` `privacy`

#### Features
- AI-powered photo tagging
- Face recognition
- Duplicate detection
- RAW photo support
- Mobile apps available
- World map and timeline views
- Privacy-focused (100% self-hosted)

#### Prerequisites
- MariaDB database (auto-configured)
- Adequate storage for photo library

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=photoprism"
```

[Learn more about PhotoPrism →](https://photoprism.app/)

</div>

### Takeout Manager {#takeout-manager}

<div class="service-card">

**Google Photos Takeout automation and management**

- **Domain**: `takeout.yourdomain.com`
- **Port**: `8000`
- **Status**: ✅ Available
- **Tags**: `media` `photos` `automation` `distributed`

#### Features
- Distributed downloads across all nodes
- Web-based job creation and monitoring
- Automatic file organization (photos/videos)
- Cookie-based authentication management
- Real-time progress tracking
- Retry failed chunks from UI

#### Prerequisites
- iSCSI block storage for database
- SMB/CIFS shares for downloads and media

#### Quick Deploy
```bash
# Build and push images
cd stacks/apps/takeout-manager
task login
task publish

# Deploy stack
cd ../../..
task ansible:deploy:stack -- -e "stack_name=takeout-manager"
```

[Learn more in the stack README →](../../stacks/apps/takeout-manager/README.md)

</div>

### Immich {#immich}

<div class="service-card">

**High-performance photo and video backup solution**

- **Domain**: `photos.yourdomain.com`
- **Port**: `2283`
- **Status**: ✅ Available
- **Tags**: `media` `photos` `ai` `backup` `sso`

#### Features
- Mobile-first photo backup (iOS and Android apps)
- Face detection and recognition (ML-powered)
- Object and scene detection
- Smart search with natural language
- Timeline and map views
- Album sharing
- Live photos support
- RAW format support

#### Authentik SSO Integration
- **Method**: OAuth/OIDC
- Auto-registration enabled

#### Prerequisites
- PostgreSQL with pgvecto.rs extension (auto-configured)
- Redis (auto-configured)
- GPU node for machine learning (optional but recommended)
- **CRITICAL**: PostgreSQL must run on local storage (not network storage) for performance

#### Storage Requirements
- Database: Local storage on dedicated node
- Photos: CIFS mount to NAS
- Upload directory: CIFS mount (read-write)
- ML cache: Local storage on GPU node

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=immich"
```

**Note**: Ensure database node label is set: `docker node update --label-add database=true <node>`

[Learn more about Immich →](https://immich.app/)

</div>

### Emby {#emby}

<div class="service-card">

**Media server for movies, TV shows, and music**

- **Domain**: `emby.yourdomain.com`
- **Port**: `8096`
- **Status**: ✅ Available
- **Tags**: `media` `streaming` `movies` `tv` `music`

#### Features
- Stream movies, TV shows, and music
- Hardware transcoding support
- Multi-user support
- Mobile and TV apps
- Live TV and DVR (with tuner)
- Parental controls
- Beautiful web interface

#### Authentik SSO Integration
- **Method**: LDAP
- Authentik provides LDAP interface on ports 389/3389

#### Storage Architecture
- **Config**: iSCSI mount (migrated in v3.4.0)
- **Media**: CIFS mount to NAS (read-only)

#### Prerequisites
- iSCSI storage for configuration
- CIFS mount for media library
- GPU for transcoding (optional)

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=emby"
```

[Learn more about Emby →](https://emby.media/)

</div>

---

## Media Automation

### Sonarr {#sonarr}

<div class="service-card">

**Automated TV show management and downloads**

- **Domain**: `sonarr.yourdomain.com`
- **Port**: `8989`
- **Status**: ✅ Available
- **Tags**: `media` `automation` `tv` `downloads`

#### Features
- Automatic TV episode downloads
- Quality profiles and cutoff
- Calendar and upcoming episodes
- Series monitoring
- Failed download handling
- Integration with download clients
- Custom formats and naming

#### Storage Requirements
- Config: iSCSI mount
- Torrents: CIFS mount (read-write)
- Usenet: CIFS mount (read-write)

#### Prerequisites
- Prowlarr for indexer management
- Download clients (qBittorrent, Deluge, SABnzbd, or NZBGet)

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=sonarr"
```

[Learn more about Sonarr →](https://sonarr.tv/)

</div>

### Radarr {#radarr}

<div class="service-card">

**Automated movie management and downloads**

- **Domain**: `radarr.yourdomain.com`
- **Port**: `7878`
- **Status**: ✅ Available
- **Tags**: `media` `automation` `movies` `downloads`

#### Features
- Automatic movie downloads
- Quality profiles and upgrades
- Calendar and upcoming releases
- Collection management
- Failed download handling
- Integration with download clients
- Custom formats and naming

#### Storage Requirements
- Config: iSCSI mount
- Torrents: CIFS mount (read-write)
- Usenet: CIFS mount (read-write)

#### Prerequisites
- Prowlarr for indexer management
- Download clients (qBittorrent, Deluge, SABnzbd, or NZBGet)

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=radarr"
```

[Learn more about Radarr →](https://radarr.video/)

</div>

### Whisparr {#whisparr}

<div class="service-card">

**Automated adult content management**

- **Domain**: `whisparr.yourdomain.com`
- **Port**: `6969`
- **Status**: ✅ Available
- **Tags**: `media` `automation` `adult` `downloads`

#### Features
- Automated adult content downloads
- Scene and performer tracking
- Quality profiles
- Integration with download clients
- Separate from regular Sonarr/Radarr

#### Storage Requirements
- Config: iSCSI mount
- Torrents: CIFS mount (read-write)
- Usenet: CIFS mount (read-write)

#### Prerequisites
- Prowlarr for indexer management
- Download clients (qBittorrent, Deluge, SABnzbd, or NZBGet)

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=whisparr"
```

[Learn more about Whisparr →](https://whisparr.com/)

</div>

### Prowlarr {#prowlarr}

<div class="service-card">

**Indexer manager for Sonarr, Radarr, and Whisparr**

- **Domain**: `prowlarr.yourdomain.com`
- **Port**: `9696`
- **Status**: ✅ Available
- **Tags**: `media` `automation` `indexer` `proxy`

#### Features
- Centralized indexer management
- Proxy aggregator for all Arr services
- Single search across multiple indexers
- Automatic sync to Sonarr/Radarr/Whisparr
- Indexer health monitoring
- Statistics and history

#### Storage Requirements
- Config: iSCSI mount

#### Prerequisites
- At least one Arr service (Sonarr, Radarr, or Whisparr)

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=prowlarr"
```

[Learn more about Prowlarr →](https://prowlarr.com/)

</div>

### Profilarr {#profilarr}

<div class="service-card">

**Profile and quality management for Arr services**

- **Domain**: `profilarr.yourdomain.com`
- **Port**: `6868`
- **Status**: ✅ Available
- **Tags**: `media` `automation` `profiles` `configuration`

#### Features
- Centralized quality profile management
- Configuration templates for Arr services
- Profile sharing across Sonarr/Radarr/Whisparr
- Automatic backup to NAS
- SQLite database (single replica)

#### Storage Requirements
- Config: iSCSI mount (read-write)
- Backup: CIFS mount (backup sidecar)

#### Prerequisites
- At least one Arr service configured

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=profilarr"
```

**Note**: Runs as single replica due to SQLite database limitation.

[Learn more about Profilarr →](https://github.com/Dictionarry-Hub/profilarr)

</div>

### FlareSolverr {#flaresolverr}

<div class="service-card">

**Cloudflare bypass proxy for indexers**

- **Domain**: Internal service (not exposed externally)
- **Port**: `8191` (internal)
- **Status**: ✅ Available
- **Tags**: `media` `automation` `proxy` `internal`

#### Features
- Bypass Cloudflare protection on indexers
- Headless browser automation
- Proxy for blocked content requests
- Used automatically by Prowlarr

#### Storage Requirements
- Config: CIFS mount

This service is primarily internal and requires no user interaction. Configure it in Prowlarr settings to enable Cloudflare-protected indexers.

[Learn more about FlareSolverr →](https://github.com/FlareSolverr/FlareSolverr)

</div>

---

## Download Clients

The downloads stack provides multiple download clients behind a VPN for privacy and security. All clients are protected by Authentik forward auth.

### Downloads Stack Overview {#downloads-stack}

<div class="service-card">

**Unified download stack with VPN and multiple clients**

- **VPN Provider**: NordVPN (OpenVPN)
- **Status**: ✅ Available
- **Tags**: `downloads` `vpn` `torrents` `usenet` `sso`

#### Stack Components
1. **VPN (Gluetun)**: NordVPN OpenVPN connection (US servers)
2. **qBittorrent**: Primary torrent client
3. **Deluge**: Alternative torrent client
4. **SABnzbd**: Primary usenet downloader
5. **NZBGet**: Lightweight usenet alternative

#### VPN Configuration
- Provider: NordVPN
- Protocol: OpenVPN
- Regions: New York, Los Angeles, Chicago, Dallas, Miami
- HTTP Proxy: Port 8888
- SOCKS5 Proxy: Port 1080

#### Authentik SSO Integration
- **Method**: Forward Auth Middleware
- All download clients protected by Authentik authentication

#### Storage Requirements
- Config per client: iSCSI mounts
- Download directories: CIFS mounts (separate for torrents/usenet)

#### Prerequisites
- NordVPN account
- iSCSI storage for configurations
- CIFS mounts for downloads
- Node labeled for downloads: `docker node update --label-add downloads=true <node>`

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=downloads"
```

**Note**: All download clients route through the VPN. If VPN connection fails, downloads stop automatically.

</div>

### qBittorrent {#qbittorrent}

<div class="service-card">

**Feature-rich torrent client with web UI**

- **Domain**: `qbittorrent.yourdomain.com`
- **Port**: `8080`
- **Status**: ✅ Available (part of downloads stack)
- **Tags**: `downloads` `torrents` `vpn` `sso`

#### Features
- Full-featured torrent client
- Sequential downloading
- RSS feed support
- Search engine integration
- IP filtering
- Web UI
- **VPN-routed for privacy**

#### Authentik SSO Integration
- Protected by forward auth middleware

[Learn more about qBittorrent →](https://www.qbittorrent.org/)

</div>

### Deluge {#deluge}

<div class="service-card">

**Lightweight torrent client with plugin support**

- **Domain**: `deluge.yourdomain.com`
- **Port**: `8112`
- **Status**: ✅ Available (part of downloads stack)
- **Tags**: `downloads` `torrents` `vpn` `sso`

#### Features
- Plugin architecture
- Daemon + web UI
- Label support
- Encryption
- **VPN-routed for privacy**

#### Authentik SSO Integration
- Protected by forward auth middleware

[Learn more about Deluge →](https://deluge-torrent.org/)

</div>

### SABnzbd {#sabnzbd}

<div class="service-card">

**Usenet download client with automation**

- **Domain**: `sabnzbd.yourdomain.com`
- **Port**: `8080`
- **Status**: ✅ Available (part of downloads stack)
- **Tags**: `downloads` `usenet` `vpn` `sso`

#### Features
- Automatic NZB handling
- Repair and extract
- RSS feed support
- API for automation
- **VPN-routed for privacy**

#### Authentik SSO Integration
- Protected by forward auth middleware

[Learn more about SABnzbd →](https://sabnzbd.org/)

</div>

### NZBGet {#nzbget}

<div class="service-card">

**Efficient binary newsreader for Usenet**

- **Domain**: `nzbget.yourdomain.com`
- **Port**: `6789`
- **Status**: ✅ Available (part of downloads stack)
- **Tags**: `downloads` `usenet` `vpn` `sso`

#### Features
- Lightweight alternative to SABnzbd
- Low resource usage
- RSS support
- Post-processing scripts
- **VPN-routed for privacy**

#### Authentik SSO Integration
- Protected by forward auth middleware

[Learn more about NZBGet →](https://nzbget.com/)

</div>

---

## Productivity & Collaboration

### CryptPad {#cryptpad}

<div class="service-card">

**Encrypted collaborative document editing**

- **Domain**: `cryptpad.yourdomain.com`
- **Port**: `3001`
- **Status**: ✅ Available
- **Tags**: `collaboration` `documents` `privacy` `encryption`

#### Features
- Real-time collaboration
- End-to-end encryption
- Document templates
- No account required
- Zero-knowledge architecture
- Rich text, spreadsheets, presentations
- Kanban boards and whiteboards

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=cryptpad"
```

[Learn more about CryptPad →](https://cryptpad.fr/)

</div>

### Mealie {#mealie}

<div class="service-card">

**Recipe management and meal planning**

- **Domain**: `mealie.yourdomain.com`
- **Port**: `9000`
- **Status**: ✅ Available
- **Tags**: `recipes` `meal-planning` `food` `sso`

#### Features
- Recipe import from URLs
- Meal planning calendar
- Shopping list generation
- Nutritional information
- Recipe scaling
- Group management
- Auto backup

#### Authentik SSO Integration
- **Method**: OAuth/OIDC
- Group-based access control (Mealie Admins, Mealie Users)
- Auto-registration enabled

#### Prerequisites
- Authentik SSO configured
- iSCSI storage for database

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=mealie"
```

[Learn more about Mealie →](https://mealie.io/)

</div>

---

## Home Automation

### Home Assistant {#home-assistant}

<div class="service-card">

**Open source home automation platform**

- **Domain**: `home.yourdomain.com`
- **Port**: `8123`
- **Status**: ✅ Available
- **Tags**: `smart-home` `automation` `iot` `privacy`

#### Features
- Control smart devices
- Automation and scenes
- Energy monitoring
- Voice assistants
- 2000+ integrations
- Mobile apps
- Local control (no cloud required)

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=homeassistant"
```

[Learn more about Home Assistant →](https://www.home-assistant.io/)

</div>

### Node-RED {#node-red}

<div class="service-card">

**Flow-based automation and programming tool**

- **Domain**: `nodered.yourdomain.com`
- **Port**: `1880`
- **Status**: ✅ Available
- **Tags**: `automation` `iot` `integration` `sso`

#### Features
- Visual programming interface
- MQTT, HTTP, WebSocket support
- 3000+ community nodes
- Integration with Home Assistant
- API endpoints creation
- Data transformation
- Persistent flows

#### Authentik SSO Integration
- **Method**: Forward Auth Middleware

#### Prerequisites
- iSCSI storage for flows

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=node-red"
```

[Learn more about Node-RED →](https://nodered.org/)

</div>

---

## AI & Chat

### LibreChat {#librechat}

<div class="service-card">

**Self-hosted AI chat interface with multiple models**

- **Domain**: `chat.yourdomain.com`
- **Port**: `3080`
- **Status**: ✅ Available
- **Tags**: `ai` `chat` `llm` `privacy`

#### Features
- Multi-model support (GPT, Claude, local models)
- Conversation history and search
- Ollama integration for local LLMs
- RAG (Retrieval-Augmented Generation)
- Vector search with embeddings
- File uploads and image generation
- Presets and plugins

#### Prerequisites
- MongoDB (auto-configured)
- Meilisearch (auto-configured)
- PostgreSQL with pgvector (auto-configured)
- RAG API (auto-configured)
- Ollama (optional, for local models)
- **Database node required**: All databases run on local storage

#### Storage Requirements
- MongoDB: Local storage on database node
- Meilisearch: Local storage on database node
- VectorDB: Local storage on database node
- Logs/Images/Uploads: CIFS mounts

#### Configuration
- Configure AI providers in `librechat.yaml`
- Ollama support for local models at `http://host.docker.internal:11434`

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=librechat"
```

**Note**: Ensure database node label is set: `docker node update --label-add database=true <node>`

[Learn more about LibreChat →](https://www.librechat.ai/)

</div>

---

## Development & ML

### MLflow {#mlflow}

<div class="service-card">

**Machine learning experiment tracking and model registry**

- **Domain**: `mlflow.yourdomain.com`
- **Port**: `5000`
- **Status**: ✅ Available
- **Tags**: `ml` `development` `experiments` `models`

#### Features
- Experiment tracking and logging
- Model registry
- Artifact storage
- Metrics visualization
- Parameter comparison
- Model versioning
- REST API

#### Storage Requirements
- Backend store: iSCSI mount
- Artifacts: iSCSI mount

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=mlflow"
```

[Learn more about MLflow →](https://mlflow.org/)

</div>

---

## Knowledge & Learning

### Kiwix {#kiwix}

<div class="service-card">

**Offline Wikipedia and knowledge base archive**

- **Domain**: `kiwix.yourdomain.com`
- **Port**: `8080`
- **Status**: ✅ Available
- **Tags**: `knowledge` `offline` `prepper` `education`

#### Features
- Offline Wikipedia access (119GB with images)
- Project Gutenberg (60,000+ ebooks)
- WikiMed (medical encyclopedia)
- Stack Overflow + Stack Exchange sites
- WikiVoyage travel guides
- OpenStreetMap Wiki
- Practical knowledge (gardening, DIY, cooking, sustainability)
- Full-text search
- No internet required after setup

#### Storage Requirements
- **Total**: ~200GB for full installation
  - Wikipedia: 119 GB
  - Project Gutenberg: 50 GB
  - WikiMed: 10 GB
  - Stack Overflow: 12 GB
  - Stack Exchange: ~5 GB each
  - FreeCodeCamp: 3 GB
  - Others: ~1-5 GB each

#### Prerequisites
- CIFS mount for ZIM files (read-only)
- Initial setup requires downloading ZIM files via `setup-nas-downloads.sh`

#### Setup Process
1. Download ZIM files to NAS (see `/stacks/apps/kiwix/ASSESSMENT.md`)
2. Deploy service
3. Access offline knowledge base

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=kiwix"
```

**Prepper/Emergency Preparedness**: This service provides critical knowledge access during network outages or emergencies.

[Learn more about Kiwix →](https://www.kiwix.org/)

</div>

---

## Core Infrastructure

### Homepage Dashboard {#homepage}

<div class="service-card">

**Centralized dashboard for all services**

- **Domain**: `dashboard.yourdomain.com`
- **Port**: `3000`
- **Status**: ✅ Available
- **Tags**: `dashboard` `monitoring` `homepage` `infrastructure`

#### Features
- Service status monitoring
- Beautiful widgets
- API integrations
- Customizable layout
- Docker integration
- Quick access to all services
- Service health checks

#### Quick Deploy
```bash
task ansible:deploy:stack -- -e "stack_name=homepage"
```

[Learn more about Homepage →](https://gethomepage.dev/)

</div>

---

## How to Add Services

Want to add a new service? It's easy!

### 1. Create Service Stack

Create a new directory and Docker Compose file:

```bash
mkdir stacks/apps/myservice
nano stacks/apps/myservice/docker-compose.yml
```

### 2. Define Your Service

```yaml
services:
  myservice:
    image: myapp:latest
    environment:
      - ENV_VAR=${ENV_VAR}
    volumes:
      - myservice_data:/data
    networks:
      - traefik-public
    deploy:
      labels:
        - traefik.enable=true
        - traefik.http.routers.myservice.rule=Host(`myapp.${BASE_DOMAIN}`)
        - traefik.http.routers.myservice.tls=true
        - traefik.http.routers.myservice.tls.certresolver=letsencrypt
        - traefik.http.services.myservice.loadbalancer.server.port=3000

networks:
  traefik-public:
    external: true

volumes:
  myservice_data:
```

### 3. Deploy Your Service

```bash
task ansible:deploy:stack -- -e "stack_name=myservice"
```

### 4. Contribute Back

Consider contributing your service definition to help others!

[Learn how to contribute →](https://github.com/chutch3/homelab/issues)

---

## Service Statistics

| Category | Services |
|----------|----------|
| Identity & Security | 2 |
| Infrastructure & Monitoring | 3 |
| Finance & Budgeting | 1 |
| Media Management | 4 |
| Media Automation | 6 |
| Download Clients | 4 (+ VPN) |
| Productivity & Collaboration | 2 |
| Home Automation | 2 |
| AI & Chat | 1 |
| Development & ML | 1 |
| Knowledge & Learning | 1 |
| Core Infrastructure | 1 |
| **Total Application Services** | **25** |

**Plus 4 Infrastructure Stacks:**
- Traefik (Reverse Proxy)
- Technitium DNS (DNS Server)
- Prometheus + Grafana (Monitoring)
- Loki + Promtail (Log Aggregation)

## Authentik SSO Integration Summary

Services integrated with Authentik SSO:

**OAuth/OIDC (Direct Integration):**
- Vaultwarden
- Immich
- Mealie

**Forward Auth (Traefik Middleware):**
- Kopia
- Node-RED
- qBittorrent
- Deluge
- SABnzbd
- NZBGet

**LDAP (Legacy Support):**
- Emby

**Total**: 10 services with SSO integration

## Storage Architecture Summary

**iSCSI Mounts** (Application data, databases, critical configs):
- `/mnt/iscsi/app-data/` - Service configurations
- `/mnt/iscsi/media-apps/` - Media automation configs
- `/mnt/iscsi/cache/` - Cache volumes

**CIFS/SMB Mounts** (Large media files, shared storage):
- Media libraries (read-only or read-write)
- Download directories
- Backup locations

**Local Storage** (Performance-critical databases):
- PostgreSQL (Immich, LibreChat)
- MongoDB (LibreChat)
- Meilisearch (LibreChat)

## Quick Start Guide

New to self-hosting? Start here:

1. **[Quick Start](../getting-started/quick-start.md)** - Get running in 5 minutes
2. **[Installation Guide](../getting-started/installation.md)** - Complete setup
3. **[Service Management](../user-guide/service-management.md)** - Learn the CLI
4. **[First Deployment](../getting-started/first-deployment.md)** - Deploy your services

**Want to add a new service?** Check the example services in `stacks/apps/` directory for reference.
