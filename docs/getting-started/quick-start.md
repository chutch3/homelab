# Quick Start Guide

!!! tip "Goal"
    Deploy your first self-hosted services in under 10 minutes!

## Prerequisites Check

Before we begin, make sure you have:

- [x] **Docker Engine 24.0+** with Docker Compose v2
- [x] **Domain name** with Cloudflare DNS management
- [x] **Cloudflare API credentials** (Global API Key or API Token)
- [x] **Linux/Unix environment** (Ubuntu 20.04+, Debian 11+, or similar)
- [x] **Network storage** (optional - for persistent data via SMB/CIFS)

!!! warning "Don't have these yet?"
    Check out our [detailed installation guide](installation.md) for step-by-step setup instructions.

## 🚀 Quick Deployment

### Step 1: Clone and Setup

```bash
git clone https://github.com/yourusername/homelab.git
cd homelab

# Copy environment template
cp .env.example .env
```

### Step 2: Configure Your Environment

Edit your `.env` file with your domain and credentials:

```bash
nano .env
```

**Essential Configuration:**

```bash title=".env"
# Your domain
BASE_DOMAIN=yourdomain.com

# Cloudflare API credentials (choose one method)
CF_Token=your_cloudflare_api_token          # ✅ Recommended method
# OR
CF_Email=your@email.com                     # Legacy method
CF_Key=your_global_api_key                  # Legacy method

# Email for SSL certificates
ACME_EMAIL=your-email@example.com

# Network storage (if you have NAS/SMB shares)
NAS_SERVER=nas.yourdomain.com
SMB_USERNAME=your_smb_username
SMB_PASSWORD=your_smb_password
```

!!! tip "Getting Cloudflare API Token"
    1. Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens)
    2. Click "Create Token"
    3. Use "Custom token" template
    4. Add permissions: `Zone:DNS:Edit` and `Zone:Zone:Read`
    5. Include your domain in "Zone Resources"

### Step 3: See Available Services

Check what services are available to deploy:

```bash
ls stacks/apps/
```

Expected output:
```
actual_server  cryptpad      deluge        emby          homeassistant
homepage       librechat     photoprism    prowlarr      qbittorrent
radarr         sonarr
```

All these services have Docker Compose files and will be deployed automatically!

### Step 4: Configure Multi-Node Setup (Optional)

If you have multiple machines for Docker Swarm:

```bash
# Copy and edit machines configuration
cp machines.yaml.example machines.yaml
nano machines.yaml
```

For single-machine setup, you can skip this step.

### Step 5: Deploy Everything

Deploy all available services:

```bash
./selfhosted.sh deploy
```

Or deploy specific services only:

```bash
# Deploy only homepage and actual budget
./selfhosted.sh deploy --only-apps homepage,actual_server

# Deploy everything except heavy services
./selfhosted.sh deploy --skip-apps photoprism,emby
```

### Step 6: Access Your Services

Once deployment completes, access your services at:

- **Homepage Dashboard**: `https://homepage.yourdomain.com`
- **Actual Budget**: `https://budget.yourdomain.com`
- **Home Assistant**: `https://homeassistant.yourdomain.com`
- **And many more...**

The Homepage dashboard will show all your deployed services!

!!! success "🎉 Congratulations!"
    You now have a complete self-hosted infrastructure running on Docker Swarm with automatic SSL certificates!

## What's Next?

<div class="grid cards" markdown>

- :material-cog: **[Service Management](../user-guide/service-management.md)**

    ---

    Learn how to add, remove, and configure services

- :material-certificate: **[SSL & Domains](../user-guide/domain-ssl.md)**

    ---

    Configure automatic SSL certificates and custom domains

- :material-harddisk: **[Volume Management](../user-guide/volume-management.md)**

    ---

    Set up persistent storage and backups with SMB/CIFS

- :material-monitor-multiple: **[Multi-Node Setup](../user-guide/multi-node.md)**

    ---

    Scale across multiple machines with Docker Swarm

</div>

## Essential Commands Reference

```bash
# Deployment Commands
./selfhosted.sh deploy                         # Deploy all services
./selfhosted.sh deploy --only-apps service1,service2  # Deploy specific services
./selfhosted.sh deploy --skip-apps service3   # Deploy all except specified

# Service Management
./selfhosted.sh redeploy-service <name>        # Redeploy single service
./selfhosted.sh nuke <service-name>            # Destroy service + volumes
./selfhosted.sh nuke                           # Destroy entire cluster

# Check Available Services
ls stacks/apps/                                # See all available services
ls stacks/apps/*/docker-compose.yml           # List services with compose files

# Docker Swarm Management
docker stack ls                                # List deployed stacks
docker stack services <stack-name>            # Show services in a stack
docker stack ps <stack-name>                  # Show tasks/containers

# Monitoring
scripts/swarm_cluster_manager.sh monitor-cluster  # Cluster health check
```

## Troubleshooting Quick Fixes

??? question "Service won't start or keeps restarting?"

    Check the service logs:
    ```bash
    # Find the service name first
    docker stack services <stack-name>

    # Check specific service logs
    docker service logs <service-name> --tail 50 --follow
    ```

??? question "Domain not resolving?"

    Verify your DNS settings:
    ```bash
    # Check if domain points to your server
    dig yourdomain.com

    # Test specific service subdomain
    dig homepage.yourdomain.com
    ```

??? question "SSL certificate issues?"

    Check Traefik and certificate status:
    ```bash
    # Check reverse-proxy stack logs
    docker stack services reverse-proxy
    docker service logs reverse-proxy_traefik --tail 50

    # Check if certificates are being generated
    docker exec -it $(docker ps -q -f name=reverse-proxy_traefik) ls -la /letsencrypt/
    ```

??? question "Volume/storage issues?"

    Check SMB/CIFS connection:
    ```bash
    # Test SMB connection manually
    smbclient -L //${NAS_SERVER} -U ${SMB_USERNAME}

    # Check volume mount status
    docker volume ls | grep <service-name>
    ```

[Need more help? See our troubleshooting guide →](../user-guide/troubleshooting.md)
