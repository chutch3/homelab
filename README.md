# 🏠 Homelab

**Docker Swarm • Pre-Configured • Production-Ready**

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?logo=docker&logoColor=white)

A Docker Swarm homelab platform with 14+ pre-configured services, automatic SSL certificates via Traefik, and network storage integration. Deploy your entire self-hosted infrastructure with one command.

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

# Configure hosts
cp ansible/inventory/03-hosts.yml.example ansible/inventory/02-hosts.yml
nano ansible/inventory/02-hosts.yml # Add your hosts and their roles

# Install Ansible and dependencies
task ansible:install

# Deploy all services
task ansible:bootstrap
task ansible:cluster:init
task ansible:deploy:full
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
- 📚 **Kiwix** - Offline Wikipedia & knowledge archive

**Media Automation:**
- 📺 **Sonarr** - TV series management
- 🎥 **Radarr** - Movie management
- 🔍 **Prowlarr** - Indexer management
- ⬇️ **qBittorrent** - BitTorrent client
- ⬇️ **Deluge** - Alternative torrent client

## 🛠️ Management Commands

All commands are run through `task`.

### Node Management
```bash
# Bootstrap all nodes (installs Docker, common packages, etc.)
task ansible:bootstrap

# Bootstrap a single node
task ansible:bootstrap:node -- worker-01

# Run a dry-run of the bootstrap process
task ansible:bootstrap:check
```

### Cluster Management
```bash
# Initialize the Docker Swarm cluster
task ansible:cluster:init

# Join worker nodes to the cluster
task ansible:cluster:join -- -e "manager_ip=... manager_token=..."

# Check the status of the cluster
task ansible:cluster:status
```

### Application Deployment
```bash
# Deploy all infrastructure and applications
task ansible:deploy:full

# Deploy only applications (skip infrastructure)
task ansible:deploy:quick

# Deploy a single stack
task ansible:deploy:stack -- -e "stack_name=sonarr"
```

### DNS Management
```bash
# Configure all DNS records (zone, A records, CNAMEs)
task ansible:dns:configure

# Create the primary DNS zone
task ansible:dns:create-zone

# Add A records for all machines
task ansible:dns:add-machines

# Add CNAME records for all services
task ansible:dns:add-services
```

### Volume Management
```bash
# List all Docker volumes
task ansible:volume:ls

# Inspect volumes for a specific service
task ansible:volume:inspect -- -e "service_name=sonarr"
```

### Teardown
```bash
# Tear down a single stack
task ansible:teardown:stack -- -e "stack_name=sonarr"

# Tear down a single stack and its volumes
task ansible:teardown:stack -- -e "stack_name=sonarr remove_volumes=true"

# Tear down all stacks (preserve volumes)
task ansible:teardown

# Complete teardown (stacks, volumes, and leave swarm)
task ansible:teardown:full
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

### Host Inventory (ansible/inventory/02-hosts.yml)

```yaml
all:
  children:
    managers:
      hosts:
        manager-01:
          ansible_host: 192.168.1.10
          ansible_user: admin
          node_labels:
            storage: true
    workers:
      hosts:
        worker-01:
          ansible_host: 192.168.1.11
          ansible_user: admin
          node_labels:
            gpu: true
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
   task ansible:deploy:stack -- -e "stack_name=myservice"
   ```

## 🏗️ How It Works

```
.env & ansible/inventory -> Ansible -> Docker Swarm → Traefik SSL → Running Services
```

**Deployment Process:**
1. **`ansible:bootstrap`**: Prepares each node with Docker and other dependencies.
2. **`ansible:cluster:init`**: Initializes the Docker Swarm on the manager.
3. **`ansible:deploy:full`**: Deploys all services as Docker Swarm stacks.
4. Traefik automatically gets SSL certificates for services with the correct labels.

**Storage:**
- Data persists on NAS via SMB/CIFS network shares.
- Configuration in environment variables.
- Services auto-configured with Traefik routing.

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
