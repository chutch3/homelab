# First Deployment

This guide walks you through your first deployment using the simplified stacks-based architecture. The homelab supports Docker Swarm deployment with Traefik reverse proxy for SSL termination and service discovery.

## Architecture Overview

The homelab uses a **stacks-based architecture** where each service is defined in its own Docker Compose file:

```
homelab/
├── .env                    # Environment configuration
├── selfhosted.sh          # 🚀 Main deployment script
├── machines.yaml           # Multi-node configuration
├── scripts/                # Management and utility scripts
│   ├── cli.sh             # Main CLI entry point
│   ├── common/            # Shared utilities
│   │   ├── ssh.sh         # SSH operations
│   │   ├── machine.sh     # Machine management
│   │   └── dns.sh         # DNS automation
│   └── docker_swarm/      # Docker Swarm implementation
│       ├── cli.sh         # Swarm command handler
│       ├── cluster.sh     # Cluster management
│       ├── deploy.sh      # Deployment logic
│       └── teardown.sh    # Cleanup and teardown
└── stacks/               # Service definitions
    ├── apps/             # Application services
    │   ├── actual_server/
    │   ├── homeassistant/
    │   ├── photoprism/
    │   └── ...
    ├── reverse-proxy/    # Traefik reverse proxy
    ├── monitoring/       # Prometheus + Grafana
    └── dns/             # Technitium DNS server
```

---

## Prerequisites

- Docker Engine 24.0+ with Docker Compose v2
- Domain with Cloudflare DNS management
- Multi-node setup (manager + workers) for Docker Swarm
- SSH access to all nodes

## Step 1: Configure Environment

### Copy and Configure .env File

```bash
# Copy the example file
cp .env.example .env

# Edit with your configuration
vim .env
```

**Essential configuration:**

```bash title=".env"
# Domain Configuration
BASE_DOMAIN=yourdomain.com
WILDCARD_DOMAIN=*.yourdomain.com

# Cloudflare API (for SSL certificates)
CF_Token=your_cloudflare_api_token

# Email for SSL certificates
ACME_EMAIL=your-email@domain.com

# User IDs for proper file permissions
UID=1000
GID=1000

# Service passwords (generate secure values)
DNS_ADMIN_PASSWORD=your_secure_dns_password
DNS_SERVER_FORWARDERS=1.1.1.1,1.0.0.1
```

### Configure Multi-Node Setup

```bash
# Copy machines example
cp machines.yaml.example machines.yaml

# Edit with your server details
vim machines.yaml
```

```yaml title="machines.yaml"
machines:
  manager:
    ip: 192.168.1.10
    user: admin
  worker-01:
    ip: 192.168.1.11
    user: admin
  worker-02:
    ip: 192.168.1.12
    user: admin
```

## Step 2: Deploy Infrastructure

### Deploy Core Services

The deployment script handles Docker Swarm setup and service deployment:

```bash
# 🚀 Deploy all infrastructure with awesome ASCII art!
./selfhosted.sh
```

This script will:
1. **Initialize Docker Swarm** cluster across your machines
2. **Create overlay network** (`traefik-public`) for service communication
3. **Deploy core stacks**:
   - **Traefik** reverse proxy with SSL termination
   - **Technitium DNS** server with local DNS records
   - **Monitoring** stack (Prometheus + Grafana)
4. **Configure DNS records** automatically for all services

### What Gets Deployed

**Core Infrastructure:**
```yaml title="stacks/reverse-proxy/docker-compose.yml"
# Traefik reverse proxy with:
# - Automatic SSL certificates via Cloudflare DNS
# - Service discovery for all applications
# - Dashboard at traefik.yourdomain.com
```

```yaml title="stacks/dns/docker-compose.yml"
# Technitium DNS server with:
# - Web interface at dns.yourdomain.com:5380
# - Automatic A/CNAME records for all services
# - Custom DNS resolution for your domain
```

## Step 3: Deploy Applications

### Individual Application Deployment

Each application is deployed as a separate stack:

```bash
# Deploy specific applications
docker stack deploy -c stacks/apps/homeassistant/docker-compose.yml homeassistant
docker stack deploy -c stacks/apps/actual_server/docker-compose.yml actual
docker stack deploy -c stacks/apps/photoprism/docker-compose.yml photoprism

# List available applications
ls stacks/apps/
```

### Available Applications

- **actual_server** - Personal finance and budgeting
- **homeassistant** - Smart home automation platform
- **photoprism** - AI-powered photo management
- **emby** - Media server and streaming
- **librechat** - AI chat interface
- **sonarr/radarr/prowlarr** - Media management suite
- **downloads** - Unified torrent stack with qBittorrent, Deluge, and VPN
- **cryptpad** - Collaborative document editing
- **homepage** - Dashboard for all services

## Step 4: Verify Deployment

### Check Service Status

```bash
# List all deployed stacks
docker stack ls

# Check specific stack services
docker stack services reverse-proxy
docker stack services dns
docker stack services monitoring

# View service logs
docker service logs reverse-proxy_traefik
docker service logs dns_dns-server
```

**Expected output:**
```
NAME                     SERVICES   ORCHESTRATOR
reverse-proxy           1          Swarm
dns                     1          Swarm
monitoring              2          Swarm
homeassistant           1          Swarm
actual                  1          Swarm
```

## Step 5: Access Your Services

All services are automatically configured with SSL certificates and accessible via your domain:

### Core Infrastructure
- **Traefik Dashboard**: `https://traefik.yourdomain.com`
- **DNS Server**: `http://dns.yourdomain.com:5380`
- **Grafana Monitoring**: `https://grafana.yourdomain.com`
- **Prometheus Metrics**: `https://prometheus.yourdomain.com`

### Applications (when deployed)
- **Home Assistant**: `https://homeassistant.yourdomain.com`
- **Actual Budget**: `https://actual.yourdomain.com`
- **PhotoPrism**: `https://photoprism.yourdomain.com`
- **Homepage Dashboard**: `https://homepage.yourdomain.com`
- **And more...**

## Management Commands

### Service Management

```bash
# Update a service (example: homeassistant)
docker service update --image homeassistant/home-assistant:latest homeassistant_homeassistant

# Scale a service
docker service scale actual_actual-server=2

# Remove a service stack
docker stack rm homeassistant

# View service logs
docker service logs -f homeassistant_homeassistant
```

### Cluster Management

```bash
# Check cluster status
./selfhosted.sh cluster status
# Or directly:
./scripts/cli.sh cluster status

# View cluster resources
docker system df
docker stats

# Complete infrastructure teardown
./selfhosted.sh teardown
# Or directly:
./scripts/cli.sh teardown
```

---

## Advanced Configuration

### Custom Service Configuration

Each service stack can be customized by editing its Docker Compose file:

```bash
# Edit a service configuration
vim stacks/apps/homeassistant/docker-compose.yml

# Redeploy with changes
docker stack deploy -c stacks/apps/homeassistant/docker-compose.yml homeassistant
```

### DNS Configuration

The system automatically configures DNS records during deployment.

```bash
# Check DNS server logs
docker service logs dns_dns-server
```

### SSL Certificates

Traefik automatically obtains SSL certificates via Cloudflare DNS challenge. Certificates are stored in Docker volumes and automatically renewed.

### Adding New Services

To add a new service:

1. **Create a new stack directory:**
   ```bash
   mkdir stacks/apps/newservice
   ```

2. **Create docker-compose.yml:**
   ```yaml title="stacks/apps/newservice/docker-compose.yml"
   services:
     newservice:
       image: newservice/image:latest
       environment:
         - EXAMPLE_VAR=${EXAMPLE_VAR}
       volumes:
         - newservice-data:/app/data
       networks:
         - traefik-public
       labels:
         - traefik.enable=true
         - traefik.http.routers.newservice.rule=Host(`newservice.${BASE_DOMAIN}`)
         - traefik.http.routers.newservice.tls=true
         - traefik.http.routers.newservice.tls.certresolver=letsencrypt
         - traefik.http.services.newservice.loadbalancer.server.port=8080

   volumes:
     newservice-data:

   networks:
     traefik-public:
       external: true
   ```

3. **Deploy the service:**
   ```bash
   docker stack deploy -c stacks/apps/newservice/docker-compose.yml newservice
   ```

---

## Troubleshooting Common Issues

### Docker Swarm Issues

??? question "Services won't start?"

    ```bash
    # Check service logs
    docker service logs servicename_containername

    # Check service status
    docker service ps servicename_containername

    # Inspect service configuration
    docker service inspect servicename_containername
    ```

??? question "Node won't join swarm?"

    ```bash
    # Check connectivity between nodes
    telnet manager-ip 2377

    # Regenerate join token on manager
    docker swarm join-token worker

    # Ensure required ports are open
    sudo ufw allow 2377/tcp  # Swarm management
    sudo ufw allow 7946/tcp  # Container network discovery
    sudo ufw allow 4789/udp  # Container overlay network
    ```

### SSL Certificate Issues

??? question "SSL certificates not working?"

    ```bash
    # Check Traefik logs
    docker service logs reverse-proxy_traefik

    # Verify Cloudflare API token
    docker service logs reverse-proxy_traefik | grep -i cloudflare

    # Check certificate storage
    docker volume inspect reverse-proxy_ssl_certs
    ```

### DNS Issues

??? question "DNS server not accessible?"

    ```bash
    # Check DNS service status
    docker service ps dns_dns-server

    # Check if accessible via host IP (not localhost)
    curl -I http://$(hostname -I | awk '{print $1}'):5380/

    # Check DNS service logs
    docker service logs dns_dns-server
    ```

### Network Issues

??? question "Services can't communicate?"

    ```bash
    # Verify overlay network exists
    docker network ls | grep traefik-public

    # Check which services are on the network
    docker network inspect traefik-public

    # Recreate network if needed
    docker network rm traefik-public
    docker network create --driver overlay traefik-public
    ```

### Complete Reset

If you need to start over completely:

```bash
# WARNING: This will destroy all data and services
./selfhosted.sh teardown

# Redeploy from scratch with style! 🚀
./selfhosted.sh deploy
```

[Next: Learn about configuration options →](configuration.md)
