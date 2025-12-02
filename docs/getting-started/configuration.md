# Configuration Guide

This guide covers all configuration options for the homelab's simplified stacks-based architecture.

## Configuration Files Overview

The homelab uses a minimal configuration approach:

```
homelab/
├── .env                        # Environment variables (your copy)
├── .env.example               # Template with all options
├── selfhosted.sh              # 🚀 Main deployment script
├── machines.yaml              # Multi-node Docker Swarm configuration
├── machines.yaml.example      # Template for machines setup
├── scripts/                   # Management and utility scripts
│   ├── cli.sh                # Main CLI entry point
│   ├── common/               # Shared utilities
│   │   ├── ssh.sh           # SSH operations
│   │   ├── machine.sh       # Machine management
│   │   └── dns.sh           # DNS automation
│   └── docker_swarm/         # Docker Swarm implementation
│       ├── cli.sh           # Swarm command handler
│       ├── cluster.sh       # Cluster management
│       ├── deploy.sh        # Deployment logic
│       └── teardown.sh      # Cleanup and teardown
└── stacks/                    # Service definitions
    ├── apps/                 # Individual applications
    ├── reverse-proxy/        # Traefik reverse proxy
    ├── monitoring/           # Prometheus + Grafana
    └── dns/                  # Technitium DNS server
```

## Environment Configuration (`.env`)

The `.env` file contains all your deployment-specific settings. Copy from `.env.example` and customize:

```bash
cp .env.example .env
vim .env
```

### Essential Configuration

```bash title=".env"
# ===========================================
# DOMAIN CONFIGURATION
# ===========================================
BASE_DOMAIN=yourdomain.com
WILDCARD_DOMAIN=*.yourdomain.com

# ===========================================
# CLOUDFLARE API CONFIGURATION
# ===========================================
# Required for automatic SSL certificates
CF_Token=your_cloudflare_api_token_here

# ===========================================
# SSL CONFIGURATION
# ===========================================
ACME_EMAIL=your-email@domain.com

# ===========================================
# DOCKER CONFIGURATION
# ===========================================
# User/Group IDs for proper file permissions
UID=1000
GID=1000

# ===========================================
# DNS SERVER CONFIGURATION
# ===========================================
# Admin password for DNS server web interface
DNS_ADMIN_PASSWORD=your_secure_dns_password

# DNS forwarders (comma-separated)
DNS_SERVER_FORWARDERS=1.1.1.1,1.0.0.1
```

### Service-Specific Configuration

The `.env` file also contains passwords and API keys for individual services:

```bash title=".env (Service Configuration)"
# ===========================================
# DATABASE CREDENTIALS
# ===========================================
# PhotoPrism database passwords
PHOTOPRISM_ADMIN_PASSWORD=your_secure_photoprism_password
PHOTOPRISM_DB_PASSWORD=your_secure_db_password
MARIADB_ROOT_PASSWORD=your_secure_root_password

# ===========================================
# MONITORING CREDENTIALS
# ===========================================
# Grafana admin password
GRAFANA_ADMIN_PASSWORD=your_secure_grafana_password

# ===========================================
# STORAGE CREDENTIALS (if using SMB/NFS)
# ===========================================
# SMB/CIFS credentials for network storage
SMB_USERNAME=your_smb_username
SMB_PASSWORD=your_secure_smb_password
SMB_DOMAIN=your_domain

# NAS server for network volumes
NAS_SERVER=nas.yourdomain.com

# ===========================================
# API KEYS (for service integrations)
# ===========================================
# Media service API keys for Homepage widgets
EMBY_API_KEY=your_emby_api_key
SONARR_API_KEY=your_sonarr_api_key
RADARR_API_KEY=your_radarr_api_key

# AI/LLM API keys for LibreChat
GROQ_API_KEY=your_groq_api_key
OPENROUTER_KEY=your_openrouter_key
```

## Multi-Node Configuration (`machines.yaml`)

For multi-node Docker Swarm deployments, configure your infrastructure in `machines.yaml`:

```bash
cp machines.yaml.example machines.yaml
vim machines.yaml
```

### Basic Configuration

```yaml title="machines.yaml"
machines:
  # Manager node (required)
  manager:
    ip: 192.168.1.10
    user: admin

  # Worker nodes (optional)
  worker-01:
    ip: 192.168.1.11
    user: admin

  worker-02:
    ip: 192.168.1.12
    user: admin
```

### Advanced Configuration

The `machines.yaml` file supports additional SSH and deployment options:

```yaml title="machines.yaml (Advanced)"
machines:
  manager:
    ip: 192.168.1.10
    user: admin
    # Optional: SSH key file (defaults to ~/.ssh/id_rsa)
    # ssh_key: ~/.ssh/homelab_rsa

  worker-01:
    ip: 192.168.1.11
    user: deploy
    # Different user per machine

  nas:
    ip: 192.168.1.100
    user: admin
    # NAS server for network storage

# Configuration is DRY - machine names become subdomains
# manager.yourdomain.com, worker-01.yourdomain.com, etc.
```

## Service Configuration

Services are configured through individual Docker Compose files in the `stacks/` directory:

### Core Services

- **Traefik** (`stacks/reverse-proxy/`) - Reverse proxy with automatic SSL
- **DNS Server** (`stacks/dns/`) - Technitium DNS with local resolution
- **Monitoring** (`stacks/monitoring/`) - Prometheus + Grafana

### Application Services

Each application has its own stack in `stacks/apps/`:

```bash
# List available applications
ls stacks/apps/

# Example: Home Assistant configuration
cat stacks/apps/homeassistant/docker-compose.yml
```

### Service Structure

Each service follows a standard pattern:

```yaml title="stacks/apps/example/docker-compose.yml"
services:
  servicename:
    image: example/image:latest
    environment:
      - EXAMPLE_VAR=${EXAMPLE_VAR}
    volumes:
      - service-data:/app/data
    networks:
      - traefik-public
    labels:
      # Traefik configuration for automatic SSL and routing
      - traefik.enable=true
      - traefik.http.routers.service.rule=Host(`service.${BASE_DOMAIN}`)
      - traefik.http.routers.service.tls=true
      - traefik.http.routers.service.tls.certresolver=letsencrypt
      - traefik.http.services.service.loadbalancer.server.port=8080

volumes:
  service-data:

networks:
  traefik-public:
    external: true
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example | Purpose |
|----------|-------------|---------|---------|
| `BASE_DOMAIN` | Your base domain | `yourdomain.com` | Service routing |
| `WILDCARD_DOMAIN` | Wildcard subdomain | `*.yourdomain.com` | SSL certificates |
| `CF_Token` | Cloudflare API token | `abc123...` | DNS challenge for SSL |
| `ACME_EMAIL` | Email for SSL certificates | `you@domain.com` | Let's Encrypt registration |

### Optional Variables

| Variable | Description | Default | Purpose |
|----------|-------------|---------|---------|
| `UID` | User ID for file permissions | `1000` | Docker volume ownership |
| `GID` | Group ID for file permissions | `1000` | Docker volume ownership |
| `DNS_ADMIN_PASSWORD` | DNS server admin password | `admin` | DNS web interface access |
| `DNS_SERVER_FORWARDERS` | Upstream DNS servers | `1.1.1.1,1.0.0.1` | DNS resolution |

### Service Passwords

Each service that requires authentication has corresponding environment variables:

```bash
# Database services
PHOTOPRISM_ADMIN_PASSWORD=secure_password
PHOTOPRISM_DB_PASSWORD=secure_db_password
MARIADB_ROOT_PASSWORD=secure_root_password

# Monitoring
GRAFANA_ADMIN_PASSWORD=secure_grafana_password

# Storage (if using network storage)
SMB_USERNAME=storage_user
SMB_PASSWORD=storage_password
```

## Deployment Scripts

### Main Deployment

```bash
# 🚀 Selfhosted Homelab Deployment Script
./selfhosted.sh

# Available commands:
./selfhosted.sh deploy          # Full deployment (default)
./selfhosted.sh cluster init    # Initialize cluster
./selfhosted.sh cluster status  # Check cluster status
./selfhosted.sh teardown        # Complete cleanup
```

This script handles:
- Docker Swarm cluster initialization
- Network creation
- Core service deployment
- DNS configuration

### Complete Cleanup

```bash
# WARNING: Removes all services and data
./selfhosted.sh teardown
```

## Configuration Examples

### Single-Node Development

```bash title=".env (Development)"
BASE_DOMAIN=local.dev
WILDCARD_DOMAIN=*.local.dev
CF_Token=your_dev_token
ACME_EMAIL=dev@local.dev

# Simple passwords for development
DNS_ADMIN_PASSWORD=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### Production Multi-Node

```bash title=".env (Production)"
BASE_DOMAIN=yourdomain.com
WILDCARD_DOMAIN=*.yourdomain.com
CF_Token=your_production_token
ACME_EMAIL=admin@yourdomain.com

# Secure passwords for production
DNS_ADMIN_PASSWORD=very_secure_password_here
GRAFANA_ADMIN_PASSWORD=another_secure_password
PHOTOPRISM_ADMIN_PASSWORD=yet_another_secure_password
```

```yaml title="machines.yaml (Production)"
machines:
  manager:
    ip: 10.0.1.10
    user: admin
  worker-01:
    ip: 10.0.1.11
    user: admin
  worker-02:
    ip: 10.0.1.12
    user: admin
```

[Next: Deploy your homelab →](first-deployment.md)
