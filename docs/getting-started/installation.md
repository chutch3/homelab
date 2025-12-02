# Installation Guide

This guide walks through installing the homelab platform.

!!! info "Prerequisites Required"
    Before installing, complete the [Prerequisites](prerequisites.md) guide to set up:

    - Docker with sudoless access
    - Cloudflare domain and API token
    - Network storage (optional)
    - SSH keys between nodes

## Quick Requirements Check

Verify you have:

- [ ] Docker installed on all nodes
- [ ] User in `docker` group (sudoless access)
- [ ] Cloudflare domain with wildcard DNS record
- [ ] Cloudflare API token with DNS permissions
- [ ] SSH access configured between nodes
- [ ] (Optional) NAS/OMV with CIFS share

## Install Platform

### 1. Clone Repository

```bash
git clone https://github.com/chutch3/selfhosted.sh.git
cd selfhosted.sh
```

### 2. Configure machines.yaml

Create your cluster configuration:

```bash
cp machines.yaml.example machines.yaml
nano machines.yaml
```

Example configuration:

```yaml
machines:
  manager:
    ip: 192.168.1.100
    ssh_user: ubuntu
    role: manager
    labels:
      storage: true

  worker-01:
    ip: 192.168.1.101
    ssh_user: ubuntu
    role: worker
    labels:
      gpu: true
```

### 3. Configure Environment

Create your `.env` file:

```bash
cp .env.example .env
nano .env
```

Essential configuration:

```bash
# Domain Configuration
BASE_DOMAIN=yourdomain.com
CF_Token=your_cloudflare_api_token_here
ACME_EMAIL=admin@yourdomain.com

# Network Storage (if using NAS)
NAS_SERVER=192.168.1.50
SMB_USERNAME=homelab
SMB_PASSWORD=your_nas_password

# Service Credentials
DNS_ADMIN_PASSWORD=secure_dns_password
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
```

See [Configuration Guide](configuration.md) for all available options.

### 4. Deploy

Initialize the cluster and deploy services:

```bash
# Initialize Docker Swarm cluster
./selfhosted.sh cluster init

# Deploy all services
./selfhosted.sh deploy
```

The deployment will:

1. Initialize Docker Swarm across your nodes
2. Create overlay networks
3. Deploy core infrastructure (Traefik, DNS, Monitoring)
4. Deploy application services
5. Configure SSL certificates automatically

### 5. Verify Deployment

Check that services are running:

```bash
# Check cluster status
./selfhosted.sh cluster status

# List deployed stacks
docker stack ls

# Check specific service
docker service logs reverse-proxy_traefik --tail 50
```

### 6. Access Services

Access your services via their domains:

- **Homepage Dashboard**: `https://homepage.yourdomain.com`
- **Traefik Dashboard**: `https://traefik.yourdomain.com`
- **Grafana Monitoring**: `https://grafana.yourdomain.com`
- **DNS Server**: `http://yourdomain.com:5380`

!!! success "Installation Complete!"
    Your homelab is now running! Check the [Service Management](../user-guide/service-management.md) guide to learn how to manage your services.

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
