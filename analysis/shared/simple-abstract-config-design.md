# Simple Abstract Configuration Design

**Date**: 2025-01-08
**Purpose**: Simplified abstract configuration that makes adding services easy
**Context**: Focus on simplicity - make it trivial to add services without worrying about infrastructure

## Executive Summary

This design prioritizes simplicity over complexity. The goal is to make adding a new service as easy as possible while abstracting away deployment-specific details. Most configuration should have sensible defaults.

## 1. Simple Service Definition

### 🎯 Minimal Service Schema

```yaml
# Simple service definition - most fields optional with smart defaults
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000                    # Single port, most common case
    # That's it! Everything else has defaults

  actual:
    image: actualbudget/actual-server:latest
    port: 5006
    storage: true                 # Just say "I need storage"

  reverse_proxy:
    image: nginx:alpine
    ports: [80, 443]              # Multiple ports when needed
    deploy: all                   # Deploy to all machines

  database:
    image: postgres:15
    port: 5432
    storage: true
    deploy: node-01               # Deploy to specific machine
```

### 🎯 Smart Defaults

```yaml
# Everything not specified gets smart defaults:
defaults:
  deploy: driver                  # Deploy to driver machine by default
  restart: unless-stopped         # Sensible restart policy
  networks: [default]             # Standard network
  domain: "${service}.${BASE_DOMAIN}"  # Auto-generate domain
  storage: false                  # No storage by default
  backup: true                    # Backup storage by default if storage: true
```

## 2. Unified Configuration (Single File)

### 📁 homelab.yaml - Everything in One Place

```yaml
# homelab.yaml - Single configuration file
version: "2.0"
deployment: docker_compose       # compose, swarm, k8s

# Environment (replaces .env)
environment:
  BASE_DOMAIN: example.com
  PROJECT_ROOT: /opt/homelab

# Infrastructure (replaces machines.yml)
machines:
  driver:
    host: 192.168.1.100
    user: ubuntu

  node-01:
    host: 192.168.1.101
    user: ubuntu

  node-02:
    host: 192.168.1.102
    user: ubuntu

# Services (replaces services.yaml + volumes.yaml)
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000

  actual:
    image: actualbudget/actual-server:latest
    port: 5006
    storage: true

  reverse_proxy:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all
```

## 3. Deployment Strategies (Simple)

### 🎯 Five Simple Deployment Options

```yaml
# Simple deployment strategies
deploy_options:
  # Don't specify = deploys to driver (default)
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000
    # deploy: driver (implicit default)

  # Deploy to all machines
  reverse_proxy:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all

  # Deploy to specific machine
  database:
    image: postgres:15
    port: 5432
    deploy: node-01

  # Deploy randomly (load balancing)
  worker_service:
    image: background-worker:latest
    deploy: random

  # Let system decide (Docker Swarm/K8s only)
  api_service:
    image: api-server:latest
    port: 8080
    deploy: any
```

## 4. Storage (Super Simple)

### 💾 Just Say "I Need Storage"

```yaml
# Storage is binary - you either need it or you don't
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000
    storage: true                 # Creates ./appdata/homepage volume

  database:
    image: postgres:15
    port: 5432
    storage: 5GB                  # Specify size if needed

  cache_service:
    image: redis:alpine
    port: 6379
    storage: temp                 # Temporary storage (no backup)
```

## 5. Translation to Deployment Types

### 🔄 Simple Translation Logic

```bash
# Simple translation - homepage example
translate_service() {
    local service="homepage"

    # From simple config:
    # image: ghcr.io/gethomepage/homepage:latest
    # port: 3000
    # (storage: false, deploy: driver - defaults)

    # To Docker Compose:
    cat <<EOF
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    ports:
      - "3000:3000"
    restart: unless-stopped
    networks:
      - default
EOF

    # Storage only added if storage: true
    # Machine assignment handled at bundle level
}
```

### 🎯 Per-Machine Bundles (Simplified)

```bash
# Generate bundle for driver machine
# Services: homepage, actual (deploy: driver by default)
generate_bundle_driver() {
    cat > docker-compose-driver.yaml <<EOF
version: '3.8'
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    ports: ["3000:3000"]
    restart: unless-stopped

  actual:
    image: actualbudget/actual-server:latest
    ports: ["5006:5006"]
    volumes: ["./appdata/actual:/data"]
    restart: unless-stopped

  reverse_proxy:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    restart: unless-stopped
EOF
}

# Generate bundle for node-01
# Services: reverse_proxy (deploy: all), database (deploy: node-01)
generate_bundle_node_01() {
    cat > docker-compose-node-01.yaml <<EOF
version: '3.8'
services:
  reverse_proxy:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    restart: unless-stopped

  database:
    image: postgres:15
    ports: ["5432:5432"]
    volumes: ["./appdata/database:/var/lib/postgresql/data"]
    restart: unless-stopped
EOF
}
```

## 6. Overrides (When You Need Them)

### 🔧 Escape Hatch for Complex Cases

```yaml
# Most services are simple, but sometimes you need more control
services:
  simple_service:
    image: simple-app:latest
    port: 8080

  complex_service:
    image: complex-app:latest
    port: 9000
    # Use overrides for complex cases
    overrides:
      environment:
        SPECIAL_CONFIG: value
        DATABASE_URL: postgres://...
      volumes:
        - "/special/path:/app/data"
      depends_on:
        - database
      # Any Docker Compose/Swarm specific config
```

## 7. Implementation (Much Simpler)

### 🛠️ Core Functions

```bash
# Main translation function (much simpler)
generate_docker_compose() {
    local target_machine="$1"

    echo "version: '3.8'"
    echo "services:"

    # Get services for this machine
    get_services_for_machine "$target_machine" | while read -r service; do
        translate_simple_service "$service"
    done
}

# Simple service translation
translate_simple_service() {
    local service="$1"

    echo "  $service:"

    # Image (required)
    local image=$(yq ".services.$service.image" homelab.yaml)
    echo "    image: $image"

    # Ports (simple)
    local port=$(yq ".services.$service.port // empty" homelab.yaml)
    local ports=$(yq ".services.$service.ports[]? // empty" homelab.yaml)

    if [ -n "$port" ]; then
        echo "    ports: [\"$port:$port\"]"
    elif [ -n "$ports" ]; then
        echo "    ports:"
        echo "$ports" | while read -r p; do
            echo "      - \"$p:$p\""
        done
    fi

    # Storage (simple)
    local storage=$(yq ".services.$service.storage // false" homelab.yaml)
    if [ "$storage" != "false" ]; then
        echo "    volumes: [\"./appdata/$service:/data\"]"
    fi

    # Defaults
    echo "    restart: unless-stopped"

    # Overrides (if any)
    apply_overrides "$service"
}

# Machine assignment (simple)
get_services_for_machine() {
    local machine="$1"

    yq '.services | to_entries[]' homelab.yaml | while read -r entry; do
        local service=$(echo "$entry" | yq '.key')
        local deploy=$(echo "$entry" | yq '.value.deploy // "driver"')

        case "$deploy" in
            "all") echo "$service" ;;
            "$machine") echo "$service" ;;
            "driver") [ "$machine" = "driver" ] && echo "$service" ;;
            "random") [ "$machine" = "$(get_random_machine)" ] && echo "$service" ;;
        esac
    done
}
```

## 8. Migration (Dead Simple)

### 🔄 Current to Simple Migration

```bash
# Simple migration script
migrate_to_simple() {
    echo "# homelab.yaml - Generated from migration" > homelab.yaml
    echo "version: '2.0'" >> homelab.yaml
    echo "deployment: docker_compose" >> homelab.yaml
    echo "" >> homelab.yaml

    # Environment from .env
    echo "environment:" >> homelab.yaml
    grep "^[A-Z]" .env | sed 's/^/  /' >> homelab.yaml
    echo "" >> homelab.yaml

    # Machines from machines.yml (if exists)
    if [ -f machines.yml ]; then
        echo "machines:" >> homelab.yaml
        yq '.managers[] | "  " + .hostname + ": {host: " + .ip + ", user: " + .user + "}"' machines.yml >> homelab.yaml
        yq '.workers[] | "  " + .hostname + ": {host: " + .ip + ", user: " + .user + "}"' machines.yml >> homelab.yaml
    else
        echo "machines:" >> homelab.yaml
        echo "  driver: {host: localhost, user: $(whoami)}" >> homelab.yaml
    fi
    echo "" >> homelab.yaml

    # Services from services.yaml
    echo "services:" >> homelab.yaml
    yq '.services | to_entries[]' config/services.yaml | while read -r entry; do
        local service=$(echo "$entry" | yq '.key')
        local image=$(echo "$entry" | yq '.value.compose.image')
        local ports=$(echo "$entry" | yq '.value.compose.ports[]? // empty' | head -1 | sed 's/.*:\([0-9]*\)"/\1/')

        echo "  $service:" >> homelab.yaml
        echo "    image: $image" >> homelab.yaml
        [ -n "$ports" ] && echo "    port: $ports" >> homelab.yaml
    done
}
```

## 9. Examples

### 📝 Real-World Simple Configuration

```yaml
# homelab.yaml - Complete example
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: homelab.local
  PROJECT_ROOT: /opt/homelab

machines:
  driver:
    host: 192.168.1.100
    user: ubuntu

services:
  # Dashboard (default: deploy to driver)
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000

  # Budget app (default: deploy to driver)
  actual:
    image: actualbudget/actual-server:latest
    port: 5006
    storage: true

  # Reverse proxy (deploy everywhere)
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all

  # Note-taking (with custom config)
  cryptpad:
    image: promasu/cryptpad:latest
    port: 3001
    storage: 2GB
    overrides:
      environment:
        CRYPTPAD_CONFIG: /etc/cryptpad/config.js
```

### 🎯 Generated Docker Compose (Driver Machine)

```yaml
# docker-compose-driver.yaml (auto-generated)
version: '3.8'
services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    ports: ["3000:3000"]
    restart: unless-stopped

  actual:
    image: actualbudget/actual-server:latest
    ports: ["5006:5006"]
    volumes: ["./appdata/actual:/data"]
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    restart: unless-stopped

  cryptpad:
    image: promasu/cryptpad:latest
    ports: ["3001:3001"]
    volumes: ["./appdata/cryptpad:/data"]
    environment:
      CRYPTPAD_CONFIG: /etc/cryptpad/config.js
    restart: unless-stopped
```

## 10. Conclusion

### ✅ Simplicity First

**Core Principle**: Adding a new service should be 3 lines:
```yaml
new_service:
  image: some-app:latest
  port: 8080
```

**Key Simplifications:**
1. **Single File**: Everything in `homelab.yaml`
2. **Smart Defaults**: Most configuration automatic
3. **Simple Deployment**: 5 options (default, all, specific, random, any)
4. **Binary Storage**: You either need it or you don't
5. **Escape Hatch**: Overrides for complex cases
6. **No Verbose Schemas**: Keep it minimal

**Benefits:**
- ✅ **Easy to Add Services**: 2-3 lines for most services
- ✅ **Single Source**: One file to rule them all
- ✅ **Deployment Agnostic**: Same config for Compose/Swarm/K8s
- ✅ **Machine Aware**: Services deploy where they should
- ✅ **Simple Migration**: Automated from current format

This design prioritizes user experience over technical completeness. It should be trivial to add a new service without understanding Docker Compose, networking, or infrastructure details.
