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
./selfhosted.sh deploy --only-apps actual_server
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
./selfhosted.sh deploy --only-apps photoprism
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
./selfhosted.sh deploy --only-apps homeassistant
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
./selfhosted.sh deploy --only-apps portainer
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
./selfhosted.sh deploy --only-apps cryptpad
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
./selfhosted.sh deploy --only-apps homepage
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
./selfhosted.sh deploy --only-apps myservice
```

### 4. Contribute Back

Consider contributing your service definition to help others!

[Learn how to contribute →](https://github.com/chutch3/selfhosted.sh/issues)

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

**Want to add a new service?** Check the example services in `stacks/apps/` directory for reference.
