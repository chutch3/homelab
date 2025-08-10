# Configuration Guide

This guide covers all configuration options and how to customize your Selfhosted deployment for different scenarios.

## Configuration Files Overview

The Selfhosted platform uses several configuration files:

```
homelab/
├── .env                        # Environment variables (your copy)
├── .env.example               # Template with all options
├── config/
│   ├── services.yaml          # Service definitions
│   ├── volumes.yaml           # Volume management
│   └── machines.yml           # Multi-node configuration
└── generated/                 # Auto-generated files
    ├── deployments/
    ├── nginx/
    └── config/
```

## Environment Configuration (`.env`)

The `.env` file contains all your deployment-specific settings.

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
# Choose ONE method:

# Method 1: API Token (Recommended)
CF_Token=your_cloudflare_api_token_here

# Method 2: Global API Key (Legacy)
# CF_Email=your@email.com
# CF_Key=your_global_api_key

# ===========================================
# DOCKER CONFIGURATION
# ===========================================
UID=1000
GID=1000
DOCKER_NETWORK=selfhosted

# ===========================================
# SECURITY CONFIGURATION
# ===========================================
ADMIN_EMAIL=admin@yourdomain.com
TIMEZONE=America/New_York
```

### Advanced Configuration

```bash title=".env (Advanced Options)"
# ===========================================
# SSH CONFIGURATION (Multi-node deployments)
# ===========================================
SSH_KEY_FILE=~/.ssh/id_rsa
SSH_TIMEOUT=30
SSH_USER=ubuntu

# ===========================================
# SSL CERTIFICATE CONFIGURATION
# ===========================================
ACME_CA_SERVER=https://acme-v02.api.letsencrypt.org/directory
ACME_EMAIL=${ADMIN_EMAIL}
CERT_RENEWAL_DAYS=30

# ===========================================
# BACKUP CONFIGURATION
# ===========================================
BACKUP_ENABLED=true
BACKUP_SCHEDULE="0 2 * * *"  # Daily at 2 AM
BACKUP_RETENTION_DAYS=30
BACKUP_LOCATION=/opt/backups

# ===========================================
# MONITORING CONFIGURATION
# ===========================================
MONITORING_ENABLED=false
PROMETHEUS_PORT=9090
GRAFANA_PORT=3001

# ===========================================
# DEVELOPMENT OPTIONS
# ===========================================
DEBUG_MODE=false
LOG_LEVEL=info
```

## Service Configuration (`config/services.yaml`)

The services configuration defines all available services and their settings.

### Basic Service Definition

```yaml title="config/services.yaml"
version: "1.0"

categories:
  finance: "Finance & Budgeting"
  media: "Media Management"
  smart_home: "Smart Home & Automation"
  development: "Development & Management"
  productivity: "Collaboration & Productivity"
  infrastructure: "Core Infrastructure"

services:
  # Simple service example
  actual:
    name: "Actual Budget"
    description: "Personal finance and budgeting application"
    category: finance
    domain: "budget"
    port: 5006
    enabled: true

    compose:
      image: "actualbudget/actual-server:latest"
      ports: ["5006:5006"]
      environment:
        - "ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB=20"
      volumes:
        - "./data/actual:/app/data"

    nginx:
      upstream: "actual_server:5006"
```

### Advanced Service Definition

```yaml title="config/services.yaml (Advanced)"
  # Advanced service with multiple platforms
  photoprism:
    name: "PhotoPrism"
    description: "AI-powered photo management and organization"
    category: media
    domain: "photos"
    port: 2342
    enabled: false

    # Docker Compose configuration
    compose:
      image: "photoprism/photoprism:latest"
      ports: ["2342:2342"]
      environment:
        - "PHOTOPRISM_ADMIN_PASSWORD=${PHOTOPRISM_ADMIN_PASSWORD}"
        - "PHOTOPRISM_SITE_URL=https://photos.${BASE_DOMAIN}"
        - "PHOTOPRISM_ORIGINALS_LIMIT=5000"
        - "PHOTOPRISM_HTTP_COMPRESSION=gzip"
        - "PHOTOPRISM_DEBUG=false"
        - "PHOTOPRISM_PUBLIC=false"
        - "PHOTOPRISM_READONLY=false"
        - "PHOTOPRISM_EXPERIMENTAL=false"
        - "PHOTOPRISM_DISABLE_CHOWN=false"
        - "PHOTOPRISM_DISABLE_WEBDAV=false"
        - "PHOTOPRISM_DISABLE_SETTINGS=false"
        - "PHOTOPRISM_DISABLE_TENSORFLOW=false"
        - "PHOTOPRISM_DISABLE_FACES=false"
        - "PHOTOPRISM_DISABLE_CLASSIFICATION=false"
        - "PHOTOPRISM_DARKTABLE_PRESETS=false"
        - "PHOTOPRISM_DETECT_NSFW=false"
        - "PHOTOPRISM_UPLOAD_NSFW=true"
        - "PHOTOPRISM_DATABASE_DRIVER=mysql"
        - "PHOTOPRISM_DATABASE_SERVER=photoprism_mariadb:3306"
        - "PHOTOPRISM_DATABASE_NAME=photoprism"
        - "PHOTOPRISM_DATABASE_USER=photoprism"
        - "PHOTOPRISM_DATABASE_PASSWORD=${PHOTOPRISM_DB_PASSWORD}"
        - "PHOTOPRISM_SITE_TITLE=PhotoPrism"
        - "PHOTOPRISM_SITE_CAPTION=AI-Powered Photos App"
        - "PHOTOPRISM_SITE_DESCRIPTION="
        - "PHOTOPRISM_SITE_AUTHOR="
      volumes:
        - "./data/photoprism/originals:/photoprism/originals"
        - "./data/photoprism/storage:/photoprism/storage"
      depends_on:
        - photoprism_mariadb
      restart: unless-stopped

    # Docker Swarm specific overrides
    swarm:
      deploy:
        mode: replicated
        replicas: 1
        placement:
          constraints:
            - node.role == manager
        resources:
          limits:
            memory: 2G
          reservations:
            memory: 1G
      volumes:
        - type: bind
          source: /mnt/media/photos
          target: /photoprism/originals
          read_only: true

    # Kubernetes specific overrides
    kubernetes:
      deployment:
        replicas: 1
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      service:
        type: ClusterIP
        port: 2342
      ingress:
        enabled: true
        className: nginx
        annotations:
          cert-manager.io/cluster-issuer: letsencrypt-prod
        tls:
          - secretName: photoprism-tls
            hosts:
              - photos.${BASE_DOMAIN}

    # Custom nginx configuration
    nginx:
      upstream: "photoprism:2342"
      additional_config: |
        client_max_body_size 500M;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        location / {
            proxy_pass http://photoprism:2342;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # WebSocket support
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        location ~ ^/(api|dav)/ {
            proxy_pass http://photoprism:2342;
            proxy_buffering off;
        }

    # Service dependencies (optional)
    dependencies:
      - photoprism_mariadb

    # Health check configuration
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:2342/api/v1/status"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Database service for PhotoPrism
  photoprism_mariadb:
    name: "PhotoPrism Database"
    description: "MariaDB database for PhotoPrism"
    category: infrastructure
    port: 3306
    enabled: false
    internal: true  # Not exposed via nginx

    compose:
      image: "mariadb:10.9"
      command: mysqld --innodb-buffer-pool-size=128M --transaction-isolation=READ-COMMITTED --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci --max-connections=512 --innodb-rollback-on-timeout=OFF --innodb-lock-wait-timeout=120
      environment:
        - "MYSQL_ROOT_PASSWORD=${PHOTOPRISM_DB_ROOT_PASSWORD}"
        - "MYSQL_DATABASE=photoprism"
        - "MYSQL_USER=photoprism"
        - "MYSQL_PASSWORD=${PHOTOPRISM_DB_PASSWORD}"
      volumes:
        - "./data/photoprism/database:/var/lib/mysql"
      restart: unless-stopped
```

## Volume Configuration (`config/volumes.yaml`)

Configure persistent storage for your services:

```yaml title="config/volumes.yaml"
version: "1.0"

# Volume definitions
volumes:
  # Local storage volumes
  local_data:
    type: local
    path: "./data"
    description: "Local service data storage"
    backup_priority: high

  local_media:
    type: local
    path: "/mnt/media"
    description: "Media files storage"
    backup_priority: medium

  # NFS storage volumes
  nfs_backup:
    type: nfs
    server: "192.168.1.100"
    path: "/volume1/backups"
    description: "NFS backup storage"
    mount_options: "nfsvers=4,rsize=1048576,wsize=1048576,hard,intr"
    backup_priority: low

  nfs_media:
    type: nfs
    server: "192.168.1.100"
    path: "/volume1/media"
    description: "NFS media storage"
    mount_options: "nfsvers=4,rsize=1048576,wsize=1048576,hard,intr"
    backup_priority: medium

# Service volume mappings
service_volumes:
  actual:
    - volume: local_data
      container_path: "/app/data"
      service_path: "actual"

  photoprism:
    - volume: nfs_media
      container_path: "/photoprism/originals"
      service_path: "photos"
      read_only: true
    - volume: local_data
      container_path: "/photoprism/storage"
      service_path: "photoprism/storage"

  homeassistant:
    - volume: local_data
      container_path: "/config"
      service_path: "homeassistant"
```

## Multi-Node Configuration (`config/machines.yml`)

For multi-node deployments:

```yaml title="config/machines.yml"
version: "1.0"

# Node definitions
nodes:
  manager:
    hostname: "manager.local"
    ip: "192.168.1.10"
    role: "manager"
    ssh_user: "ubuntu"
    ssh_port: 22
    labels:
      - "node.type=manager"
      - "storage.type=ssd"
    resources:
      cpu_cores: 8
      memory_gb: 32
      storage_gb: 500

  worker1:
    hostname: "worker1.local"
    ip: "192.168.1.11"
    role: "worker"
    ssh_user: "ubuntu"
    ssh_port: 22
    labels:
      - "node.type=worker"
      - "storage.type=hdd"
      - "media.node=true"
    resources:
      cpu_cores: 4
      memory_gb: 16
      storage_gb: 2000

  worker2:
    hostname: "worker2.local"
    ip: "192.168.1.12"
    role: "worker"
    ssh_user: "ubuntu"
    ssh_port: 22
    labels:
      - "node.type=worker"
      - "storage.type=ssd"
      - "compute.node=true"
    resources:
      cpu_cores: 6
      memory_gb: 24
      storage_gb: 1000

# Service placement rules
placement:
  # Database services on SSD storage
  databases:
    constraints:
      - "storage.type==ssd"

  # Media services on nodes with large storage
  media:
    constraints:
      - "media.node==true"

  # Compute-intensive services
  compute:
    constraints:
      - "compute.node==true"
```

## Environment Variables Reference

### Domain Configuration

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `BASE_DOMAIN` | Your base domain | `yourdomain.com` | ✅ |
| `WILDCARD_DOMAIN` | Wildcard subdomain | `*.yourdomain.com` | ✅ |

### Cloudflare API

| Variable | Description | Example | Required |
|----------|-------------|---------|----------|
| `CF_Token` | API Token (recommended) | `abc123...` | ✅* |
| `CF_Email` | Account email (legacy) | `you@email.com` | ✅* |
| `CF_Key` | Global API Key (legacy) | `def456...` | ✅* |

*Choose either Token OR Email+Key

### Docker Configuration

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `UID` | User ID for file permissions | `1000` | ❌ |
| `GID` | Group ID for file permissions | `1000` | ❌ |
| `DOCKER_NETWORK` | Docker network name | `selfhosted` | ❌ |

### Service-Specific Variables

Generated automatically based on enabled services:

```bash
# Domain mappings (auto-generated)
DOMAIN_ACTUAL=budget.yourdomain.com
DOMAIN_PHOTOPRISM=photos.yourdomain.com
DOMAIN_HOMEASSISTANT=home.yourdomain.com

# Service-specific secrets
PHOTOPRISM_ADMIN_PASSWORD=secure_password_here
PHOTOPRISM_DB_PASSWORD=database_password_here
PHOTOPRISM_DB_ROOT_PASSWORD=root_password_here
```

## Validation and Testing

### Validate Configuration

```bash
# Validate all configuration files
./selfhosted config validate

# Check specific components
./selfhosted config validate --env
./selfhosted config validate --services
./selfhosted config validate --volumes
```

### Test Configuration

```bash
# Test service generation
./selfhosted service generate --dry-run

# Test specific deployment type
./selfhosted deploy compose validate
./selfhosted deploy swarm validate
```

## Configuration Examples

### Development Environment

```bash title=".env (Development)"
BASE_DOMAIN=localhost
WILDCARD_DOMAIN=*.localhost

# Skip SSL for local development
SSL_ENABLED=false
ACME_STAGING=true

# Debug options
DEBUG_MODE=true
LOG_LEVEL=debug
```

### Production Environment

```bash title=".env (Production)"
BASE_DOMAIN=yourdomain.com
WILDCARD_DOMAIN=*.yourdomain.com

# Production SSL
CF_Token=your_production_token
SSL_ENABLED=true
ACME_CA_SERVER=https://acme-v02.api.letsencrypt.org/directory

# Security hardening
DEBUG_MODE=false
LOG_LEVEL=warn
MONITORING_ENABLED=true
BACKUP_ENABLED=true
```

### Multi-Node Cluster

```bash title=".env (Cluster)"
BASE_DOMAIN=cluster.yourdomain.com
WILDCARD_DOMAIN=*.cluster.yourdomain.com

# Cluster configuration
DEPLOYMENT_TYPE=swarm
SWARM_MANAGER_IP=192.168.1.10
CLUSTER_NODES=3

# Shared storage
NFS_SERVER=192.168.1.100
NFS_MOUNT_OPTIONS=nfsvers=4,hard,intr
```

[Next: Choose your deployment type →](first-deployment.md)
