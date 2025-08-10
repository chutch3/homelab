# Service Management

Learn how to effectively manage services in your Selfhosted platform with comprehensive examples and real-world scenarios.

## Overview

The Selfhosted platform provides powerful service management capabilities through a unified CLI interface and YAML configuration system.

### Core Concepts

- **Services**: Individual applications defined in `config/services.yaml`
- **Categories**: Logical groupings (finance, media, development, etc.)
- **Enablement**: Control which services are deployed via `enabled: true/false`
- **Generation**: Automatic creation of deployment files from service definitions

---

## Service Discovery

### List All Available Services

```bash
# Show all services with status
./selfhosted service list
```

Output:
```
🎯 Available Services (12):

📊 Finance & Budgeting:
  ✅ actual              - Actual Budget - Personal finance and budgeting
  ❌ firefly             - Firefly III - Personal finance manager

📸 Media Management:
  ❌ photoprism          - PhotoPrism - AI-powered photo management
  ❌ jellyfin            - Jellyfin - Media server and streaming
  ❌ immich              - Immich - Self-hosted photo backup

🏠 Smart Home & Automation:
  ❌ homeassistant       - Home Assistant - Open source home automation
  ❌ nodered             - Node-RED - Flow-based programming

🔧 Development & Management:
  ❌ portainer           - Portainer Agent - Container management interface
  ❌ gitea               - Gitea - Self-hosted Git service

📝 Collaboration & Productivity:
  ✅ cryptpad            - CryptPad - Encrypted collaborative editing
  ❌ nextcloud           - NextCloud - File sync and collaboration

🌐 Core Infrastructure:
  ✅ homepage            - Homepage Dashboard - Centralized dashboard

Legend: ✅ Enabled | ❌ Disabled
```

### Filter Services by Category

```bash
# List only media services
./selfhosted service list --category media

# List only enabled services
./selfhosted service list --enabled

# List only disabled services
./selfhosted service list --disabled
```

### Get Service Information

```bash
# Get detailed information about a service
./selfhosted service info actual
```

Output:
```
📊 Actual Budget (actual)

Description: Personal finance and budgeting application
Category: Finance & Budgeting
Status: ✅ Enabled
Domain: budget.yourdomain.com (https://budget.yourdomain.com)
Port: 5006

📦 Container Configuration:
  Image: actualbudget/actual-server:latest
  Ports: 5006:5006
  Volumes: ./data/actual:/app/data
  Environment:
    - ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB=20

🌐 Nginx Configuration:
  Upstream: actual_server:5006
  SSL: Enabled
  Custom Config: Standard proxy configuration

🔧 Deployment Support:
  ✅ Docker Compose
  ✅ Docker Swarm
  ❌ Kubernetes (planned)

📋 Dependencies: None
```

---

## Service Enablement

### Enable Services

```bash
# Enable a single service
./selfhosted service enable actual

# Enable multiple services
./selfhosted service enable homepage actual cryptpad

# Enable all services in a category
./selfhosted service enable --category media
```

### Disable Services

```bash
# Disable a single service
./selfhosted service disable actual

# Disable multiple services
./selfhosted service disable photoprism jellyfin

# Disable all services in a category
./selfhosted service disable --category development
```

### Interactive Service Selection

```bash
# Launch interactive service selector
./selfhosted service interactive
```

Interactive interface:
```
┌─ Service Selection ─────────────────────────────────────┐
│                                                         │
│ 📊 Finance & Budgeting:                                │
│  [x] actual      - Actual Budget                       │
│  [ ] firefly     - Firefly III                         │
│                                                         │
│ 📸 Media Management:                                    │
│  [ ] photoprism  - PhotoPrism                          │
│  [x] jellyfin    - Jellyfin                            │
│  [ ] immich      - Immich                              │
│                                                         │
│ 🏠 Smart Home & Automation:                            │
│  [x] homeassistant - Home Assistant                    │
│                                                         │
│ ↑/↓: Navigate | Space: Toggle | Enter: Apply | Q: Quit │
└─────────────────────────────────────────────────────────┘
```

### Bulk Operations

```bash
# Enable all services (be careful!)
./selfhosted service enable --all

# Disable all services
./selfhosted service disable --all

# Reset to default enabled services
./selfhosted service reset --defaults
```

---

## Service Status and Monitoring

### Check Service Status

```bash
# Show enabled services
./selfhosted service status
```

Output:
```
✅ Enabled Services (3):

📊 Finance & Budgeting:
  actual       - https://budget.yourdomain.com

📝 Collaboration & Productivity:
  cryptpad     - https://cryptpad.yourdomain.com

🌐 Core Infrastructure:
  homepage     - https://dashboard.yourdomain.com

Total: 3 services enabled
```

### Validate Service Configuration

```bash
# Validate all service configurations
./selfhosted service validate

# Validate specific service
./selfhosted service validate actual

# Validate services by category
./selfhosted service validate --category media
```

Validation output:
```
🔍 Validating Service Configurations...

✅ actual: Configuration valid
  ✅ Docker image exists: actualbudget/actual-server:latest
  ✅ Port 5006 is available
  ✅ Volume path valid: ./data/actual
  ✅ Environment variables valid
  ✅ Nginx configuration valid

✅ homepage: Configuration valid
  ✅ Docker image exists: ghcr.io/gethomepage/homepage:latest
  ✅ Port 3000 is available
  ✅ Volume path valid: ./data/homepage
  ✅ Docker socket accessible

⚠️  cryptpad: Configuration warning
  ✅ Docker image exists: promasu/cryptpad:latest
  ✅ Port 3001 is available
  ⚠️  Large volume detected: ./data/cryptpad (consider external storage)

📊 Validation Summary:
  ✅ Valid: 2 services
  ⚠️  Warnings: 1 service
  ❌ Errors: 0 services
```

---

## File Generation

### Generate Deployment Files

```bash
# Generate all deployment files for enabled services
./selfhosted service generate

# Generate for specific platform
./selfhosted service generate --platform compose
./selfhosted service generate --platform swarm
./selfhosted service generate --platform kubernetes

# Dry run (show what would be generated)
./selfhosted service generate --dry-run
```

Generation output:
```
🔧 Generating deployment files...

📁 Creating directory structure:
  ✅ generated/deployments/
  ✅ generated/nginx/templates/
  ✅ generated/config/

📦 Generating Docker Compose files:
  ✅ generated/deployments/docker-compose.yaml
  ✅ generated/deployments/docker-compose.override.yaml

🌐 Generating Nginx configurations:
  ✅ generated/nginx/templates/actual.template
  ✅ generated/nginx/templates/homepage.template
  ✅ generated/nginx/templates/cryptpad.template

⚙️  Generating configuration files:
  ✅ generated/config/domains.env
  ✅ generated/config/enabled-services.list

📋 Generation complete! Files ready for deployment.
```

### Clean Generated Files

```bash
# Remove all generated files
./selfhosted service clean

# Remove specific platform files
./selfhosted service clean --platform compose
```

---

## Advanced Service Management

### Custom Service Configuration

#### Override Environment Variables

```yaml title="config/services.yaml"
actual:
  name: "Actual Budget"
  # ... other config
  compose:
    environment:
      - "ACTUAL_UPLOAD_FILE_SYNC_SIZE_LIMIT_MB=50"  # Increased limit
      - "ACTUAL_HTTPS_PORT=5007"                    # Custom port
      - "ACTUAL_DATABASE_URL=${ACTUAL_DB_URL}"      # External database
```

#### Custom Volume Mounts

```yaml title="config/services.yaml"
photoprism:
  name: "PhotoPrism"
  # ... other config
  compose:
    volumes:
      - "./data/photoprism/storage:/photoprism/storage"
      - "/mnt/nas/photos:/photoprism/originals:ro"  # Read-only originals
      - "/mnt/ssd/cache:/photoprism/cache"          # Fast cache storage
```

#### Platform-Specific Overrides

```yaml title="config/services.yaml"
jellyfin:
  name: "Jellyfin"
  # ... base config

  # Docker Compose configuration
  compose:
    image: "jellyfin/jellyfin:latest"
    devices:
      - "/dev/dri:/dev/dri"  # Hardware acceleration

  # Docker Swarm overrides
  swarm:
    deploy:
      placement:
        constraints:
          - "node.labels.gpu==true"  # Deploy on GPU nodes
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  # Kubernetes overrides
  kubernetes:
    deployment:
      nodeSelector:
        hardware.gpu: "true"
      resources:
        limits:
          nvidia.com/gpu: 1
```

### Service Dependencies

Define dependencies between services:

```yaml title="config/services.yaml"
wordpress:
  name: "WordPress"
  # ... other config
  dependencies:
    - mysql
    - redis

  compose:
    depends_on:
      mysql:
        condition: service_healthy
      redis:
        condition: service_started

mysql:
  name: "MySQL Database"
  # ... mysql config
  internal: true  # Not exposed via nginx

  compose:
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Health Checks

Configure health monitoring:

```yaml title="config/services.yaml"
nextcloud:
  name: "NextCloud"
  # ... other config

  compose:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/status.php"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Swarm health checks
  swarm:
    deploy:
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
        window: 120s
```

---

## Service Profiles and Environments

### Create Service Profiles

Define different service combinations for different use cases:

```yaml title="config/profiles.yaml"
profiles:
  minimal:
    description: "Minimal self-hosting setup"
    services:
      - homepage
      - actual

  media_server:
    description: "Complete media management"
    services:
      - homepage
      - jellyfin
      - sonarr
      - radarr
      - qbittorrent
      - photoprism

  smart_home:
    description: "Smart home automation"
    services:
      - homepage
      - homeassistant
      - nodered
      - mosquitto
      - zigbee2mqtt

  development:
    description: "Development environment"
    services:
      - homepage
      - gitea
      - jenkins
      - portainer
      - postgresql
      - redis
```

Apply profiles:

```bash
# Apply a profile
./selfhosted service profile apply media_server

# List available profiles
./selfhosted service profile list

# Show profile contents
./selfhosted service profile show development
```

### Environment-Specific Configuration

```bash
# Set environment
export SELFHOSTED_ENV=development

# Environment-specific service files
config/
├── services.yaml              # Base configuration
├── services.development.yaml  # Development overrides
├── services.staging.yaml      # Staging overrides
└── services.production.yaml   # Production overrides
```

---

## Service Templates

### Create Custom Service Templates

```yaml title="templates/custom-service.yaml"
# Template for custom PHP applications
custom_php_app:
  name: "${SERVICE_NAME}"
  description: "${SERVICE_DESCRIPTION}"
  category: "${SERVICE_CATEGORY:-custom}"
  domain: "${SERVICE_DOMAIN}"
  port: "${SERVICE_PORT:-80}"
  enabled: false

  compose:
    image: "${PHP_IMAGE:-php:8.2-apache}"
    ports: ["${SERVICE_PORT:-80}:80"]
    environment:
      - "DB_HOST=${DB_HOST:-mysql}"
      - "DB_NAME=${DB_NAME}"
      - "DB_USER=${DB_USER}"
      - "DB_PASSWORD=${DB_PASSWORD}"
    volumes:
      - "./data/${SERVICE_DOMAIN}:/var/www/html"
    depends_on:
      - mysql

  nginx:
    upstream: "${SERVICE_DOMAIN}:${SERVICE_PORT:-80}"
    additional_config: |
      location ~ \.php$ {
          proxy_pass http://${SERVICE_DOMAIN}:${SERVICE_PORT:-80};
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
      }
```

Use templates:

```bash
# Create service from template
./selfhosted service create --template custom-php-app \
  --name "My Blog" \
  --domain "blog" \
  --description "Personal blog" \
  --category "personal"
```

---

## Monitoring and Maintenance

### Service Logs

```bash
# View service logs (Docker Compose)
./selfhosted service logs actual

# Follow logs in real-time
./selfhosted service logs --follow actual

# View logs from all services
./selfhosted service logs --all

# View last 100 lines
./selfhosted service logs --tail 100 actual
```

### Service Metrics

```bash
# Show resource usage
./selfhosted service stats

# Monitor specific service
./selfhosted service stats actual

# Export metrics to file
./selfhosted service stats --export metrics.json
```

Output:
```
📊 Service Resource Usage:

┌─────────────┬─────────┬─────────┬─────────────┬─────────────┐
│ Service     │ CPU %   │ Memory  │ Disk I/O    │ Network I/O │
├─────────────┼─────────┼─────────┼─────────────┼─────────────┤
│ actual      │ 2.3%    │ 156MB   │ 1.2MB/s     │ 45KB/s      │
│ homepage    │ 0.8%    │ 89MB    │ 0.1MB/s     │ 12KB/s      │
│ cryptpad    │ 1.1%    │ 234MB   │ 0.8MB/s     │ 67KB/s      │
│ nginx       │ 0.3%    │ 23MB    │ 0.3MB/s     │ 156KB/s     │
└─────────────┴─────────┴─────────┴─────────────┴─────────────┘

Total CPU: 4.5% | Total Memory: 502MB
```

### Backup and Restore

```bash
# Backup service data
./selfhosted service backup actual

# Backup all enabled services
./selfhosted service backup --all

# Restore service from backup
./selfhosted service restore actual --from backup-20241215.tar.gz

# List available backups
./selfhosted service backup list
```

### Update Services

```bash
# Update specific service image
./selfhosted service update actual

# Update all services
./selfhosted service update --all

# Check for available updates
./selfhosted service check-updates
```

---

## Troubleshooting

### Common Issues

??? question "Service won't start?"

    ```bash
    # Check service logs
    ./selfhosted service logs actual

    # Validate configuration
    ./selfhosted service validate actual

    # Check port conflicts
    sudo netstat -tulpn | grep :5006

    # Verify Docker image
    docker pull actualbudget/actual-server:latest
    ```

??? question "Service shows as enabled but not generating?"

    ```bash
    # Check service status
    ./selfhosted service status

    # Regenerate files
    ./selfhosted service clean
    ./selfhosted service generate

    # Validate YAML syntax
    ./selfhosted config validate
    ```

??? question "Nginx not proxying correctly?"

    ```bash
    # Check nginx configuration
    cat generated/nginx/templates/actual.template

    # Test nginx config
    docker exec nginx nginx -t

    # Reload nginx
    docker exec nginx nginx -s reload
    ```

### Debug Mode

Enable debug output for troubleshooting:

```bash
# Enable debug mode
export DEBUG=true

# Run commands with verbose output
./selfhosted service generate --debug
./selfhosted service validate --verbose
```

[Next: Learn about deployment options →](deployment-options.md)
