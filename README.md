# 🏠 Homelab

**Docker Swarm • Pre-Configured • Production-Ready**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)

A Docker Swarm homelab platform with 13+ pre-configured services, automatic SSL certificates via Traefik, and network storage integration. Deploy your entire self-hosted infrastructure with one command.

## 🚀 Quick Start

**Requirements:**
- Docker with Compose v2
- Domain name with Cloudflare DNS
- Cloudflare API token

**Deploy everything:**
```bash
git clone https://github.com/yourusername/homelab.git
cd homelab

# Configure environment
cp .env.example .env
nano .env  # Add your domain and Cloudflare token

# Deploy all services
./selfhosted.sh deploy
```

Access your services at `https://homepage.yourdomain.com`

## 📦 Pre-Configured Services

**Infrastructure:**
- 🌐 **Technitium DNS** - Local DNS server
- 🚪 **Traefik** - Reverse proxy with automatic SSL
- 📊 **Prometheus + Grafana** - System monitoring

**Applications:**
- 🏠 **Homepage** - Service dashboard
- 💰 **Actual Budget** - Personal finance
- 🏡 **Home Assistant** - Smart home automation
- 📸 **PhotoPrism** - Photo management
- 🎬 **Emby** - Media server
- 📝 **CryptPad** - Collaborative documents
- 🤖 **LibreChat** - AI chat interface

**Media Automation:**
- 📺 **Sonarr** - TV series management
- 🎥 **Radarr** - Movie management
- 🔍 **Prowlarr** - Indexer management
- ⬇️ **qBittorrent** - BitTorrent client
- ⬇️ **Deluge** - Alternative torrent client

## 🛠️ Management Commands

```bash
# Deploy all services
./selfhosted.sh deploy                    # Full deployment (infrastructure + apps)
./selfhosted.sh deploy --skip-infra       # Quick app updates (skip infrastructure)

# Deployment options
./selfhosted.sh deploy --skip-infra --only-apps homepage  # Update single app
./selfhosted.sh deploy --skip-apps photoprism             # Skip specific apps
./selfhosted.sh deploy --only-apps sonarr,radarr          # Deploy only specific apps

# Cluster management
./selfhosted.sh cluster init              # Initialize Swarm cluster
./selfhosted.sh cluster status            # Check cluster status
./selfhosted.sh cluster join <node>       # Join worker node to cluster

# Volume management
./selfhosted.sh volume ls                 # List all Docker volumes
./selfhosted.sh volume ls photoprism      # List volumes for specific service
./selfhosted.sh volume inspect photoprism # Inspect volume configuration
./selfhosted.sh volume diff photoprism    # Compare current vs compose file config
./selfhosted.sh volume recreate photoprism --backup  # Recreate with backup
./selfhosted.sh volume recreate photoprism --force   # Skip confirmation

# Cleanup
./selfhosted.sh teardown                  # Complete cleanup

# Advanced: Direct CLI usage
./scripts/cli.sh deploy                   # Deploy via CLI
./scripts/cli.sh deploy --skip-infra      # Quick updates via CLI
./scripts/cli.sh cluster init -c machines.yaml
./scripts/cli.sh cluster status
./scripts/cli.sh teardown
```

## ⚙️ Configuration

### Environment Variables (.env)

```bash
# Domain & SSL
BASE_DOMAIN=yourdomain.com
CF_Token=your_cloudflare_api_token
ACME_EMAIL=admin@yourdomain.com

# Network Storage (optional)
NAS_SERVER=nas.yourdomain.com
SMB_USERNAME=your_username
SMB_PASSWORD=your_password

# Service credentials
GRAFANA_ADMIN_PASSWORD=secure_password
# ... more service passwords
```

### Multi-Node Setup (machines.yaml)

```yaml
machines:
  manager:
    ip: 192.168.1.10
    role: manager
    ssh_user: admin

  worker:
    ip: 192.168.1.11
    role: worker
    ssh_user: admin
```

## 📁 Adding Services

1. **Create compose file:**
   ```bash
   mkdir stacks/apps/myservice
   nano stacks/apps/myservice/docker-compose.yml
   ```

2. **Include Traefik labels:**
   ```yaml
   version: "3.9"
   services:
     myservice:
       image: myapp:latest
       networks:
         - traefik-public
       deploy:
         labels:
           - "traefik.enable=true"
           - "traefik.http.routers.myservice.rule=Host(`myapp.${BASE_DOMAIN}`)"
           - "traefik.http.routers.myservice.tls.certresolver=dns"

   networks:
     traefik-public:
       external: true
   ```

3. **Deploy:**
   ```bash
   ./selfhosted.sh deploy --only-apps myservice
   ```

## 🏗️ How It Works

```
.env config → Docker Swarm → Traefik SSL → Running Services
```

**Deployment Process:**
1. Sets up Docker Swarm cluster
2. Deploys DNS and Traefik infrastructure
3. Deploys application services in parallel
4. Traefik automatically gets SSL certificates

**Storage:**
- Data persists on NAS via SMB/CIFS network shares
- Configuration in environment variables
- Services auto-configured with Traefik routing

## 🔧 Development

```bash
# Install dependencies
task install

# Run all tests
task test

# Run linting
task lint

# Complete CI check
task check
```

## 🤝 Contributing

1. Write tests first (TDD approach)
2. Use conventional commit messages
3. Update documentation for changes

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

**Deploy your entire homelab in minutes** ⚡
