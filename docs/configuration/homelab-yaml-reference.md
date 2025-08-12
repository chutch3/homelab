# homelab.yaml Configuration Reference

**Version**: 2.0
**Purpose**: Unified configuration file for simplified homelab deployment

## Overview

The `homelab.yaml` file is the single configuration file that defines your entire homelab setup. It replaces the previous multi-file approach (`services.yaml` + `machines.yml` + `volumes.yaml` + `.env`) with a simple, unified configuration.

## Security Best Practices

### Environment Variables and Sensitive Data

**IMPORTANT**: Never commit sensitive data directly to `homelab.yaml`. Instead, use a `.env` file for sensitive environment variables:

1. **Create a `.env` file** in your project root:
   ```bash
   # Cloudflare API credentials
   CF_Key=your_cloudflare_api_key_here
   CF_Email=your_cloudflare_email@example.com

   # Service API Keys and Credentials
   EMBY_API_KEY=your_emby_api_key
   HASS_TOKEN=your_homeassistant_long_lived_token
   RADARR_API_KEY=your_radarr_api_key
   SONARR_API_KEY=your_sonarr_api_key
   DELUGE_PASSWORD=your_deluge_password
   QBIT_USERNAME=admin
   QBIT_PASSWORD=your_qbit_password
   PROWLARR_API_KEY=your_prowlarr_api_key
   ```

2. **Reference variables in homelab.yaml** using comments to indicate they're loaded from .env:
   ```yaml
   environment:
     # These are loaded from .env file
     # CF_Key: ${CF_Key}
     # CF_Email: ${CF_Email}
   ```

3. **The .env file is automatically ignored** by git to protect your sensitive data.

### Environment Variable Loading Priority

The system loads environment variables in the following order (later values override earlier ones):
1. System environment variables
2. Variables from `.env` file (if present)
3. Variables defined directly in `homelab.yaml`

## Schema Structure

### Required Fields

#### `version` (string, required)
- **Value**: `"2.0"`
- **Purpose**: Configuration schema version
- **Example**: `version: "2.0"`

#### `deployment` (string, required)
- **Values**: `docker_compose`, `docker_swarm`, `kubernetes`
- **Purpose**: Target deployment type (mutually exclusive)
- **Example**: `deployment: docker_compose`

#### `services` (object, required)
- **Purpose**: Service definitions
- **Minimum**: At least one service required
- **Example**: See [Services Section](#services)

### Optional Fields

#### `environment` (object, optional)
- **Purpose**: Global environment variables
- **Pattern**: Variable names must be UPPERCASE with underscores
- **Example**:
  ```yaml
  environment:
    BASE_DOMAIN: homelab.local
    PROJECT_ROOT: /opt/homelab
    TIMEZONE: America/New_York
  ```

#### `machines` (object, optional)
- **Purpose**: Machine definitions for multi-node deployments
- **Required for**: Multi-machine Docker Compose, Docker Swarm
- **Example**: See [Machines Section](#machines)

## Machines

Machine definitions specify the infrastructure for multi-node deployments.

### Machine Object Structure

```yaml
machines:
  machine-name:
    host: "192.168.1.100"        # Required: IP or hostname
    user: "ubuntu"               # Required: SSH username
    role: "manager"              # Optional: manager|worker (Swarm only)
    labels:                      # Optional: Custom labels
      - "storage=ssd"
      - "gpu=nvidia"
```

### Machine Name Rules
- Must be lowercase alphanumeric with hyphens
- Examples: `driver`, `node-01`, `homelab-main`

### Required Machine Fields

#### `host` (string, required)
- **Purpose**: IP address or hostname for SSH connection
- **Examples**: `192.168.1.100`, `homelab.local`, `node-01.example.com`

#### `user` (string, required)
- **Purpose**: SSH username for remote access
- **Examples**: `ubuntu`, `pi`, `homelab`

### Optional Machine Fields

#### `role` (string, optional)
- **Values**: `manager`, `worker`
- **Purpose**: Docker Swarm role designation
- **Default**: `worker`
- **Note**: Only used for `docker_swarm` deployment

#### `labels` (array, optional)
- **Purpose**: Custom labels for service placement constraints
- **Format**: Array of strings
- **Examples**: `["storage=ssd", "gpu=nvidia", "zone=us-east"]`

## Services

Service definitions specify what applications to deploy and how.

### Service Object Structure

```yaml
services:
  service-name:
    image: "nginx:alpine"        # Required: Docker image
    port: 80                     # Optional: Single port
    ports: [80, 443]            # Optional: Multiple ports
    storage: true               # Optional: Persistent storage
    deploy: "all"               # Optional: Deployment strategy
    enabled: true               # Optional: Enable/disable
    environment:                # Optional: Service env vars
      VAR_NAME: "value"
    overrides:                  # Optional: Deployment-specific config
      docker_compose: {}
```

### Service Name Rules
- Must be lowercase alphanumeric with hyphens
- Examples: `homepage`, `home-assistant`, `media-server`

### Required Service Fields

#### `image` (string, required)
- **Purpose**: Docker image name and tag
- **Examples**:
  - `nginx:alpine`
  - `ghcr.io/gethomepage/homepage:latest`
  - `actualbudget/actual-server:latest`

### Optional Service Fields

#### `port` (integer, optional)
- **Purpose**: Single port exposure
- **Range**: 1-65535
- **Example**: `port: 3000`
- **Note**: Cannot use both `port` and `ports`

#### `ports` (array, optional)
- **Purpose**: Multiple port exposures
- **Format**: Array of integers (1-65535)
- **Example**: `ports: [80, 443, 8080]`
- **Note**: Cannot use both `port` and `ports`

#### `storage` (boolean or string, optional)
- **Purpose**: Persistent storage configuration
- **Values**:
  - `true`: Enable default persistent storage
  - `false`: No persistent storage
  - `"5GB"`, `"100MB"`, `"1TB"`: Storage with size limit
  - `"temp"`: Temporary storage (cleared on restart)
- **Examples**:
  ```yaml
  storage: true          # Default storage
  storage: "10GB"        # 10GB storage limit
  storage: "temp"        # Temporary storage
  storage: false         # No storage
  ```

#### `deploy` (string, optional)
- **Purpose**: Deployment strategy
- **Default**: `"driver"`
- **Values**:
  - `"driver"`: Deploy to driver machine only
  - `"all"`: Deploy to all machines
  - `"random"`: Deploy to randomly selected machine
  - `"any"`: Let system choose machine
  - `"machine-name"`: Deploy to specific machine
- **Examples**:
  ```yaml
  deploy: "all"          # All machines
  deploy: "node-01"      # Specific machine
  deploy: "random"       # Random placement
  ```

#### `enabled` (boolean, optional)
- **Purpose**: Enable or disable service
- **Default**: `true`
- **Example**: `enabled: false`

#### `environment` (object, optional)
- **Purpose**: Service-specific environment variables
- **Pattern**: Variable names must be UPPERCASE with underscores
- **Example**:
  ```yaml
  environment:
    DATABASE_URL: "postgres://user:pass@db:5432/app"
    API_KEY: "${SECRET_API_KEY}"
  ```

#### `overrides` (object, optional)
- **Purpose**: Deployment-specific configuration overrides
- **Use Case**: Complex configurations that don't fit the simple model
- **Structure**:
  ```yaml
  overrides:
    docker_compose:
      # Docker Compose specific config
      depends_on: ["database"]
      networks: ["custom_network"]
    docker_swarm:
      # Docker Swarm specific config
      replicas: 3
      placement:
        constraints: ["node.role == worker"]
    kubernetes:
      # Kubernetes specific config (future)
  ```

## Deployment Strategies

### Single Machine (`docker_compose`)
```yaml
version: "2.0"
deployment: docker_compose

machines:
  driver:
    host: localhost
    user: homelab

services:
  app:
    image: nginx:alpine
    port: 80
```

### Multi-Machine (`docker_compose`)
```yaml
version: "2.0"
deployment: docker_compose

machines:
  driver: {host: 192.168.1.100, user: ubuntu}
  node-01: {host: 192.168.1.101, user: ubuntu}

services:
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all          # Deploy to all machines

  app:
    image: myapp:latest
    port: 3000
    deploy: node-01      # Deploy to specific machine
```

### Docker Swarm (`docker_swarm`)
```yaml
version: "2.0"
deployment: docker_swarm

machines:
  manager:
    host: 192.168.1.100
    user: ubuntu
    role: manager
  worker-01:
    host: 192.168.1.101
    user: ubuntu
    role: worker

services:
  web:
    image: nginx:alpine
    port: 80
    deploy: any          # Let Swarm schedule
    overrides:
      docker_swarm:
        replicas: 3      # Scale across cluster
```

## Validation

### Schema Validation
```bash
# Validate against JSON schema
./scripts/validate_homelab_schema.sh homelab.yaml

# Validate with verbose output
./scripts/validate_homelab_schema.sh -v homelab.yaml

# Validate specific example
./scripts/validate_homelab_schema.sh examples/homelab-basic.yaml
```

### Common Validation Errors

#### Missing Required Fields
```yaml
# ❌ Invalid: Missing required fields
version: "2.0"
# Missing deployment and services

# ✅ Valid: All required fields present
version: "2.0"
deployment: docker_compose
services:
  app:
    image: nginx:alpine
```

#### Invalid Port Configuration
```yaml
# ❌ Invalid: Both port and ports specified
services:
  app:
    image: nginx:alpine
    port: 80
    ports: [80, 443]  # Cannot use both

# ✅ Valid: Single port
services:
  app:
    image: nginx:alpine
    port: 80

# ✅ Valid: Multiple ports
services:
  app:
    image: nginx:alpine
    ports: [80, 443]
```

#### Invalid Machine References
```yaml
machines:
  driver: {host: localhost, user: ubuntu}

services:
  app:
    image: nginx:alpine
    deploy: "node-01"  # ❌ Invalid: machine doesn't exist

# ✅ Valid: Reference existing machine
services:
  app:
    image: nginx:alpine
    deploy: "driver"   # References defined machine
```

## Migration from Legacy Configuration

### From services.yaml
```yaml
# Old services.yaml
services:
  homepage:
    enabled: true
    compose:
      image: ghcr.io/gethomepage/homepage:latest
      ports: ["3000:3000"]

# New homelab.yaml
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000
```

### From machines.yml
```yaml
# Old machines.yml
managers:
  - hostname: homelab-driver
    ip: 192.168.1.100
    user: ubuntu

# New homelab.yaml
machines:
  homelab-driver:
    host: 192.168.1.100
    user: ubuntu
```

## Best Practices

### 1. Use Simple Deployment Strategies
```yaml
# ✅ Good: Simple and clear
services:
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all

# ❌ Avoid: Complex overrides unless necessary
services:
  nginx:
    image: nginx:alpine
    overrides:
      docker_compose:
        ports: ["80:80", "443:443"]
        # Use simple 'ports' field instead
```

### 2. Leverage Smart Defaults
```yaml
# ✅ Good: Minimal configuration
services:
  app:
    image: myapp:latest
    port: 3000
    # enabled: true (default)
    # deploy: "driver" (default)

# ❌ Avoid: Redundant explicit defaults
services:
  app:
    image: myapp:latest
    port: 3000
    enabled: true    # Redundant
    deploy: "driver" # Redundant
```

### 3. Use Environment Variables
```yaml
# ✅ Good: Centralized environment config
environment:
  BASE_DOMAIN: homelab.local
  DATABASE_PASSWORD: "${DB_PASS}"

services:
  app:
    image: myapp:latest
    environment:
      DOMAIN: "${BASE_DOMAIN}"
      DB_PASSWORD: "${DATABASE_PASSWORD}"
```

### 4. Group Related Services
```yaml
# ✅ Good: Logical grouping and naming
services:
  # Infrastructure
  nginx:
    image: nginx:alpine
    deploy: all

  # Management
  homepage:
    image: gethomepage/homepage:latest
    deploy: driver

  # Applications
  actual-budget:
    image: actualbudget/actual-server:latest
    deploy: node-01
```

## Troubleshooting

### Validation Issues
- **Invalid YAML**: Check indentation and syntax
- **Schema errors**: Run validation script for detailed errors
- **Missing fields**: Ensure `version`, `deployment`, and `services` are present

### Machine Connection Issues
- **SSH access**: Ensure machines are accessible via SSH with specified user
- **Host resolution**: Use IP addresses if hostnames don't resolve
- **User permissions**: Ensure SSH user has Docker access

### Service Deployment Issues
- **Port conflicts**: Check for duplicate port assignments
- **Machine references**: Ensure deploy targets reference valid machines
- **Image availability**: Verify Docker images exist and are accessible

## Examples

See the `examples/` directory for complete configuration examples:
- `examples/homelab-basic.yaml` - Single machine setup
- `examples/homelab-multi-node.yaml` - Multi-machine Docker Compose
- `examples/homelab-swarm.yaml` - Docker Swarm with orchestration
