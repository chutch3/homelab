# Configuration Guide

This guide covers all configuration options for the homelab's simplified stacks-based architecture.

## Configuration Files Overview

The homelab uses a minimal configuration approach:

```
homelab/
├── .env                        # Environment variables (your copy)
├── .env.example               # Template with all options
├── ansible/                    # Ansible configuration and playbooks
│   ├── inventory/              # Host inventory and variables
│   │   ├── 02-hosts.yml        # Your host definitions
│   │   └── group_vars/         # Variables for groups of hosts
│   ├── playbooks/              # Ansible playbooks for all actions
│   └── roles/                  # Reusable Ansible roles
├── Taskfile.yml                # 🚀 Main command interface
└── stacks/                     # Service definitions
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

# ===========================================
# CLOUDFLARE API CONFIGURATION
# ===========================================
# Required for automatic SSL certificates
CF_Token=your_cloudflare_api_token_here

# ===========================================
# DOCKER CONFIGURATION
# ===========================================
# User/Group IDs for proper file permissions
UID=1000
GID=1000

# ===========================================
# DNS SERVER CONFIGURATION
# ===========================================
# PRIMARY_DNS_MANAGED=true:  this repo deploys and manages the DNS server (stacks/dns)
# PRIMARY_DNS_MANAGED=false: bring your own DNS — set PRIMARY_DNS_HOST to your server
PRIMARY_DNS_TYPE=technitium
PRIMARY_DNS_MANAGED=true
PRIMARY_DNS_API_KEY=your_secure_dns_admin_password

# DNS forwarders (comma-separated, Technitium only)
DNS_SERVER_FORWARDERS=1.1.1.1,1.0.0.1

# ===========================================
# SECONDARY DNS — OPTIONAL
# ===========================================
# Enable to keep a secondary DNS server in sync so services resolve when the primary is down.
# Supported types: pihole (requires v6.3+, uses REST API at http://<host>/api).
# IMPORTANT: Pi-hole must have app_sudo enabled to allow API writes:
#   sudo pihole-FTL --config webserver.api.app_sudo true
SECONDARY_DNS_ENABLED=false
SECONDARY_DNS_TYPE=pihole
SECONDARY_DNS_HOST=192.168.1.x
SECONDARY_DNS_API_KEY=your_secondary_dns_api_password
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

## Multi-Node Configuration

For multi-node Docker Swarm deployments, configure your infrastructure in the Ansible inventory. You should create a file named `ansible/inventory/02-hosts.yml` and add your server details.

```bash
# Create and edit your hosts file
nano ansible/inventory/02-hosts.yml
```

**Example `ansible/inventory/02-hosts.yml`:**

```yaml
all:
  children:
    managers:
      hosts:
        manager:
          ansible_host: 192.168.1.100   # Example IP
          ansible_user: ubuntu           # Example user
          node_labels:
            storage: true

    workers:
      hosts:
        worker-01:
          ansible_host: 192.168.1.101
          ansible_user: ubuntu
          node_labels:
            gpu: true
            gpu_model: "NVIDIA RTX 3090"

        worker-02:
          ansible_host: 192.168.1.102
          ansible_user: ubuntu
          node_labels:
            storage: true

    gpu_nodes:
      hosts:
        worker-01:
```

The Ansible inventory supports a wide range of variables for host and group configuration. See the [Ansible documentation](https://docs.ansible.com/ansible/latest/user_guide/intro_inventory.html) for more information.

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
      - traefik.http.routers.service.tls.certresolver=dns
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
| `CF_Token` | Cloudflare API token | `abc123...` | DNS challenge for SSL |
| `PRIMARY_DNS_API_KEY` | DNS server admin password | `secure_password` | DNS web interface / API access |

### Optional Variables

| Variable | Description | Default | Purpose |
|----------|-------------|---------|---------|
| `UID` | User ID for file permissions | `1000` | Docker volume ownership |
| `GID` | Group ID for file permissions | `1000` | Docker volume ownership |
| `PRIMARY_DNS_TYPE` | DNS provider type | `technitium` | Selects the primary DNS adapter |
| `PRIMARY_DNS_MANAGED` | Repo deploys the DNS server | `true` | Set `false` to bring your own DNS |
| `PRIMARY_DNS_API_KEY` | DNS server admin password | _(required)_ | DNS web interface / API access |
| `DNS_SERVER_FORWARDERS` | Upstream DNS servers | `1.1.1.1,1.0.0.1` | DNS resolution |
| `SECONDARY_DNS_ENABLED` | Enable secondary DNS sync | `false` | Keeps a fallback DNS in sync |
| `SECONDARY_DNS_TYPE` | Secondary DNS provider type | `pihole` | Selects the secondary DNS adapter |
| `SECONDARY_DNS_HOST` | Secondary DNS server IP | _(none)_ | Required when secondary DNS is enabled |
| `SECONDARY_DNS_API_KEY` | Secondary DNS API password | _(none)_ | Required when secondary DNS is enabled |

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

## Secrets Management

The homelab includes a Bitwarden-backed secrets system for syncing your `.env`, Ansible hosts file, and SSH config across machines. This lets you wipe local secrets from a workstation and restore them later without losing anything.

### Login and Unlock the Vault

```bash
task secrets:login
```

For non-interactive use (CI or scripts), set `BW_CLIENTID`, `BW_CLIENTSECRET`, and `BW_PASSWORD` in your environment.

### Push Local Secrets to the Vault

```bash
task secrets:push
```

Uploads `.env`, `ansible/inventory/02-hosts.yml`, and `ansible/inventory/group_vars/all/ssh.yml` as Bitwarden file attachments.

### Restore Secrets from the Vault

```bash
task secrets:pull
```

Downloads and writes all three files from the vault to their local paths.

### Securely Wipe Local Secrets

```bash
task secrets:wipe
```

Removes the local `.env`, hosts file, and SSH config. Run `secrets:pull` to restore them.

---

## Deployment Commands

### Main Deployment

```bash
# 🚀 Homelab Deployment with Ansible
task ansible:bootstrap   # install Docker and dependencies on all nodes
task ansible:deploy      # init Swarm, join workers, deploy all stacks
```

This sequence will:
- Bootstrap all nodes with Docker and security hardening
- Initialize Docker Swarm and join all workers
- Deploy all infrastructure and application stacks

### Complete Cleanup

```bash
# WARNING: Removes all services (preserves volumes)
task ansible:teardown

# Remove all services and data (DESTRUCTIVE)
task ansible:teardown:with-volumes
```

## Configuration Examples

### Single-Node Development

```bash title=".env (Development)"
BASE_DOMAIN=local.dev
CF_Token=your_dev_token

# Simple passwords for development
PRIMARY_DNS_API_KEY=admin
GRAFANA_ADMIN_PASSWORD=admin
```

### Production Multi-Node

```bash title=".env (Production)"
BASE_DOMAIN=yourdomain.com
CF_Token=your_production_token

# Secure passwords for production
PRIMARY_DNS_API_KEY=very_secure_password_here
GRAFANA_ADMIN_PASSWORD=another_secure_password
PHOTOPRISM_ADMIN_PASSWORD=yet_another_secure_password
```

```yaml title="ansible/inventory/02-hosts.yml (Production)"
all:
  children:
    managers:
      hosts:
        manager:
          ansible_host: 10.0.1.10
          ansible_user: admin
    workers:
      hosts:
        worker-01:
          ansible_host: 10.0.1.11
          ansible_user: admin
        worker-02:
          ansible_host: 10.0.1.12
          ansible_user: admin
```

[Next: Deploy your homelab →](installation.md)
