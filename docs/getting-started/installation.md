# Installation Guide

## Requirements

- **Linux server** (Ubuntu 20.04+ recommended)
- **Docker** with Docker Compose v2
- **Domain name** managed by Cloudflare
- **Cloudflare API token**

## Install Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Test Docker works
docker --version
docker compose version
```

## Get Cloudflare API Token

1. Go to [Cloudflare API Tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click "Create Token" → "Custom token"
3. Add permissions: `Zone:DNS:Edit` and `Zone:Zone:Read`
4. Include your domain in "Zone Resources"
5. Copy the token

## Setup DNS

Point your domain to your server:

```
Type: A
Name: *
Content: YOUR_SERVER_IP
```

Set "Proxy status" to **DNS only** (gray cloud).

## Install Platform

```bash
# Clone repository
git clone https://github.com/yourusername/homelab.git
cd homelab

# Copy and edit configuration
cp .env.example .env
nano .env

# Add your domain and Cloudflare token
BASE_DOMAIN=yourdomain.com
CF_Token=your_cloudflare_token_here
ACME_EMAIL=admin@yourdomain.com

# Deploy everything
./selfhosted.sh deploy
```

That's it! Access your services at `https://homepage.yourdomain.com`

## Troubleshooting

**Docker permission denied?**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**Services won't start?**
```bash
docker service logs service_name --tail 50
```

**SSL certificate issues?**
Test your Cloudflare token:
```bash
curl -X GET "https://api.cloudflare.com/client/v4/zones" \
     -H "Authorization: Bearer YOUR_TOKEN"
```
