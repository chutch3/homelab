# Quick Start Guide

!!! tip "Goal"
    Get your first self-hosted service running in under 5 minutes!

## Prerequisites Check

Before we begin, make sure you have:

- [x] **Docker Engine 24.0+** with Docker Compose v2
- [x] **Domain name** with Cloudflare DNS management
- [x] **Cloudflare API credentials** (Global API Key or API Token)
- [x] **Linux/Unix environment** (Ubuntu 20.04+, Debian 11+, or similar)

!!! warning "Don't have these yet?"
    Check out our [detailed installation guide](installation.md) for step-by-step setup instructions.

## 🚀 5-Minute Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/yourusername/homelab.git
cd homelab
```

### Step 2: Initialize Your Environment

```bash
./selfhosted config init
```

This command will:

- Copy `.env.example` to `.env`
- Guide you through basic configuration
- Validate your setup

### Step 3: Configure Essential Variables

Edit your `.env` file with your domain and Cloudflare credentials:

```bash
nano .env
```

**Required Configuration:**

```bash title=".env"
# Your domain
BASE_DOMAIN=yourdomain.com

# Cloudflare API credentials (choose one method)
CF_Token=your_cloudflare_api_token          # ✅ Recommended method
# OR
CF_Email=your@email.com                     # Legacy method
CF_Key=your_global_api_key                  # Legacy method
```

!!! tip "Getting Cloudflare API Token"
    1. Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens)
    2. Click "Create Token"
    3. Use "Custom token" template
    4. Add permissions: `Zone:DNS:Edit` and `Zone:Zone:Read`
    5. Include your domain in "Zone Resources"

### Step 4: Explore Available Services

See what services you can deploy:

```bash
./selfhosted service list
```

Expected output:
```
🎯 Available Services (6):

📊 Finance & Budgeting:
  ✅ actual              - Actual Budget - Personal finance and budgeting

📸 Media Management:
  ❌ photoprism          - PhotoPrism - AI-powered photo management

🏠 Smart Home & Automation:
  ❌ homeassistant       - Home Assistant - Open source home automation

🔧 Development & Management:
  ❌ portainer           - Portainer Agent - Container management interface

📝 Collaboration & Productivity:
  ❌ cryptpad            - CryptPad - Encrypted collaborative editing

🌐 Core Infrastructure:
  ✅ homepage            - Homepage Dashboard - Centralized dashboard
```

### Step 5: Enable Your First Service

Let's start with a simple service - Homepage Dashboard:

```bash
./selfhosted service enable homepage
```

Or use the interactive selector:

```bash
./selfhosted service interactive
```

### Step 6: Generate Deployment Files

```bash
./selfhosted service generate
```

This creates:

- `generated/deployments/docker-compose.yaml` - Docker Compose configuration
- `generated/nginx/templates/` - Nginx reverse proxy templates
- `generated/config/domains.env` - Domain environment variables

### Step 7: Deploy Your Services

```bash
./selfhosted deploy compose up
```

### Step 8: Access Your Services

Once deployment is complete, access your services:

- **Homepage Dashboard**: `https://dashboard.yourdomain.com`

!!! success "🎉 Congratulations!"
    You now have your first self-hosted service running! The Homepage Dashboard will show all your available services.

## What's Next?

<div class="grid cards" markdown>

- :material-plus-circle: **[Add More Services](../services/index.md)**

    ---

    Browse our catalog of 20+ available services

- :material-cog: **[Service Management](../user-guide/service-management.md)**

    ---

    Learn advanced service configuration and management

- :material-certificate: **[SSL & Domains](../user-guide/domain-ssl.md)**

    ---

    Configure automatic SSL certificates and custom domains

- :material-harddisk: **[Volume Management](../user-guide/volume-management.md)**

    ---

    Set up persistent storage and backups

</div>

## Quick Commands Reference

```bash
# Service Management
./selfhosted service list              # List all services
./selfhosted service enable <name>     # Enable a service
./selfhosted service disable <name>    # Disable a service
./selfhosted service status           # Show enabled services

# Deployment
./selfhosted service generate         # Generate deployment files
./selfhosted deploy compose up        # Start services
./selfhosted deploy compose down      # Stop services

# Configuration
./selfhosted config validate          # Validate configuration
./selfhosted help                     # Show detailed help
```

## Troubleshooting Quick Fixes

??? question "Service won't start?"

    Check the logs:
    ```bash
    docker compose logs <service-name>
    ```

??? question "Domain not resolving?"

    Verify your DNS settings:
    ```bash
    dig dashboard.yourdomain.com
    ```

??? question "SSL certificate issues?"

    Check certificate status:
    ```bash
    docker compose exec nginx ls -la /etc/nginx/certs/
    ```

[Need more help? See our troubleshooting guide →](../user-guide/troubleshooting.md)
