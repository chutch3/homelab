# Available Services

Browse our comprehensive catalog of self-hosted services. Each service is pre-configured and ready to deploy with a single command.

## Service Categories

<div class="grid cards" markdown>

- :material-chart-line: **[Finance & Budgeting](#finance-budgeting)**

    ---

    Manage your personal finances and track expenses

    **1 service available**

- :material-image: **[Media Management](#media-management)**

    ---

    Organize and stream your photos, videos, and music

    **3 services planned**

- :material-home-automation: **[Smart Home & Automation](#smart-home-automation)**

    ---

    Automate your home with open-source solutions

    **2 services available**

- :material-code-braces: **[Development & Management](#development-management)**

    ---

    Development tools and container management

    **1 service available**

- :material-file-document: **[Collaboration & Productivity](#collaboration-productivity)**

    ---

    Document editing and team collaboration

    **1 service available**

- :material-server: **[Core Infrastructure](#core-infrastructure)**

    ---

    Essential services for your self-hosted setup

    **1 service available**

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

#### Quick Deploy
```bash
./selfhosted service enable actual
./selfhosted service generate
./selfhosted deploy compose up
```

#### Configuration
```yaml
actual:
  name: "Actual Budget"
  description: "Personal finance and budgeting application"
  category: finance
  domain: "budget"
  port: 5006
  enabled: true

  compose:
    image: "actualbudget/actual-server:latest"
    ports: ["5006:5006"]
    environment:
      - "ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB=20"
    volumes:
      - "./data/actual:/app/data"
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

#### Prerequisites
- MariaDB database (auto-configured)
- Adequate storage for photo library

#### Quick Deploy
```bash
./selfhosted service enable photoprism
./selfhosted service generate
./selfhosted deploy compose up
```

[Learn more about PhotoPrism →](https://photoprism.app/)

</div>

### Jellyfin {#jellyfin}

<div class="service-card">

**Media server and streaming platform**

- **Domain**: `media.yourdomain.com`
- **Port**: `8096`
- **Status**: 🔄 Planned
- **Tags**: `media` `streaming` `movies` `tv`

#### Features
- Stream movies, TV shows, music
- Hardware acceleration support
- Mobile and TV apps
- No subscription fees
- Complete privacy

#### Coming Soon
This service is planned for the next release. Want to help implement it?

[Contribute to Jellyfin integration →](https://github.com/chutch3/selfhosted.sh/issues)

</div>

---

## Smart Home & Automation

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

#### Quick Deploy
```bash
./selfhosted service enable homeassistant
./selfhosted service generate
./selfhosted deploy compose up
```

[Learn more about Home Assistant →](https://www.home-assistant.io/)

</div>

---

## Development & Management

### Portainer Agent {#portainer}

<div class="service-card">

**Container management interface**

- **Domain**: `portainer.yourdomain.com`
- **Port**: `9000`
- **Status**: ✅ Available
- **Tags**: `containers` `management` `docker` `development`

#### Features
- Visual Docker management
- Container monitoring
- Stack deployment
- User management
- Template library

#### Quick Deploy
```bash
./selfhosted service enable portainer
./selfhosted service generate
./selfhosted deploy compose up
```

[Learn more about Portainer →](https://www.portainer.io/)

</div>

---

## Collaboration & Productivity

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

#### Quick Deploy
```bash
./selfhosted service enable cryptpad
./selfhosted service generate
./selfhosted deploy compose up
```

[Learn more about CryptPad →](https://cryptpad.fr/)

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

#### Quick Deploy
```bash
./selfhosted service enable homepage
./selfhosted service generate
./selfhosted deploy compose up
```

[Learn more about Homepage →](https://gethomepage.dev/)

</div>

---

## How to Add Services

Want to add a new service? It's easy!

### 1. Add Service Definition

Add your service to `config/services.yaml`:

```yaml
myservice:
  name: "My Service"
  description: "What it does"
  category: productivity
  domain: "myapp"
  port: 3000
  enabled: false

  compose:
    image: "myapp:latest"
    ports: ["3000:3000"]
    environment:
      - "ENV_VAR=value"
    volumes:
      - "./data/myapp:/app/data"

  nginx:
    upstream: "myservice:3000"
```

### 2. Enable and Deploy

```bash
./selfhosted service enable myservice
./selfhosted service generate
./selfhosted deploy compose up
```

### 3. Contribute Back

Consider contributing your service definition to help others!

[Learn how to contribute →](../development/contributing.md)

---

## Service Statistics

| Category | Available | Planned | Total |
|----------|-----------|---------|-------|
| Finance & Budgeting | 1 | 2 | 3 |
| Media Management | 1 | 5 | 6 |
| Smart Home | 1 | 3 | 4 |
| Development | 1 | 4 | 5 |
| Collaboration | 1 | 3 | 4 |
| Infrastructure | 1 | 8 | 9 |
| **Total** | **6** | **25** | **31** |

## Quick Start Guide

New to selfhosted? Start here:

1. **[Quick Start](../getting-started/quick-start.md)** - Get running in 5 minutes
2. **[Installation Guide](../getting-started/installation.md)** - Complete setup
3. **[Service Management](../user-guide/service-management.md)** - Learn the CLI
4. **[First Deployment](../getting-started/first-deployment.md)** - Deploy your services

[Next: Learn about adding services →](adding-services.md)
