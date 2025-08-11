# Simple Implementation Plan - Unified Configuration

**Date**: 2025-01-08
**Purpose**: Implementation plan for simplified unified configuration approach
**Context**: Focus on simplicity - make adding services trivial

## Executive Summary

This implementation plan focuses on the simplified approach where adding a service is just 2-3 lines in a single `homelab.yaml` file. The goal is to eliminate complexity while maintaining deployment flexibility.

## 1. Proof of Concept (Week 1)

### 🧪 PoC Goal: 3 Services, Single File

#### Target Configuration:
```yaml
# homelab.yaml (PoC)
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: homelab.local

machines:
  driver: {host: localhost, user: ubuntu}

services:
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000

  actual:
    image: actualbudget/actual-server:latest
    port: 5006
    storage: true

  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all
```

#### PoC Deliverables:
```bash
# Week 1 deliverables
deliverables:
  homelab_schema: "Simple YAML schema validation"
  basic_translator: "homelab.yaml → docker-compose.yaml"
  simple_generator: "Generate machine bundles"
  poc_test: "Deploy 3 services successfully"
```

## 2. Implementation Tasks

### 📅 Day 1-2: Core Schema and Validation

```bash
# Create simple schema validator
create_schema_validator() {
    # File: scripts/validate_homelab_yaml.sh

    # Required fields
    check_required_field "version"
    check_required_field "deployment"
    check_required_field "services"

    # Validate each service has image
    for service in $(yq '.services | keys[]' homelab.yaml); do
        check_service_has_image "$service"
    done

    echo "✅ homelab.yaml is valid"
}

# Simple service validation
check_service_has_image() {
    local service="$1"
    local image=$(yq ".services.$service.image // empty" homelab.yaml)

    if [ -z "$image" ]; then
        echo "❌ Service $service missing required 'image' field"
        exit 1
    fi
}
```

### 📅 Day 3-4: Basic Translation Engine

```bash
# Core translation: homelab.yaml → docker-compose.yaml
translate_to_docker_compose() {
    local target_machine="${1:-driver}"

    echo "version: '3.8'"
    echo "services:"

    # Get services for this machine
    get_services_for_machine "$target_machine" | while read -r service; do
        echo "  $service:"

        # Image (required)
        local image=$(yq ".services.$service.image" homelab.yaml)
        echo "    image: $image"

        # Ports (simple logic)
        translate_ports "$service"

        # Storage (simple logic)
        translate_storage "$service"

        # Defaults
        echo "    restart: unless-stopped"

        # Overrides (if any)
        translate_overrides "$service"
    done
}

# Simple port translation
translate_ports() {
    local service="$1"

    # Single port
    local port=$(yq ".services.$service.port // empty" homelab.yaml)
    if [ -n "$port" ]; then
        echo "    ports: [\"$port:$port\"]"
        return
    fi

    # Multiple ports
    local ports=$(yq ".services.$service.ports[]? // empty" homelab.yaml)
    if [ -n "$ports" ]; then
        echo "    ports:"
        echo "$ports" | while read -r p; do
            echo "      - \"$p:$p\""
        done
    fi
}

# Simple storage translation
translate_storage() {
    local service="$1"
    local storage=$(yq ".services.$service.storage // false" homelab.yaml)

    case "$storage" in
        "true")
            echo "    volumes: [\"./appdata/$service:/data\"]"
            ;;
        "temp")
            echo "    volumes: [\"/tmp/appdata/$service:/data\"]"
            ;;
        *[0-9]*) # Size specified (e.g., "5GB")
            echo "    volumes: [\"./appdata/$service:/data\"]"
            # TODO: Add size limits in future
            ;;
    esac
}
```

### 📅 Day 5: Machine Assignment Logic

```bash
# Simple machine assignment
get_services_for_machine() {
    local target_machine="$1"

    yq '.services | to_entries[]' homelab.yaml | while read -r entry; do
        local service=$(echo "$entry" | yq '.key')
        local deploy=$(echo "$entry" | yq '.value.deploy // "driver"')

        case "$deploy" in
            "all")
                echo "$service"
                ;;
            "$target_machine")
                echo "$service"
                ;;
            "driver")
                if [ "$target_machine" = "driver" ]; then
                    echo "$service"
                fi
                ;;
            "random")
                # For PoC, just assign to driver
                if [ "$target_machine" = "driver" ]; then
                    echo "$service"
                fi
                ;;
            "any")
                # For PoC, just assign to driver
                if [ "$target_machine" = "driver" ]; then
                    echo "$service"
                fi
                ;;
        esac
    done
}

# Get all machines
get_all_machines() {
    # Driver machine
    echo "driver"

    # Additional machines
    yq '.machines | keys[]' homelab.yaml 2>/dev/null | grep -v "driver" || true
}
```

## 3. Week 2-3: Complete Implementation

### 📅 Week 2: Multi-Machine Support

```bash
# Day 6-7: Bundle generation per machine
generate_all_bundles() {
    local deployment_type=$(yq '.deployment' homelab.yaml)

    get_all_machines | while read -r machine; do
        echo "🔧 Generating bundle for $machine..."

        case "$deployment_type" in
            "docker_compose")
                translate_to_docker_compose "$machine" > "docker-compose-$machine.yaml"
                ;;
            "docker_swarm")
                translate_to_docker_swarm "$machine" > "docker-stack-$machine.yaml"
                ;;
        esac

        # Generate nginx config for this machine
        generate_nginx_config "$machine" > "nginx-$machine.conf"

        echo "✅ Generated bundle for $machine"
    done
}

# Day 8-10: Integration with existing system
integrate_with_existing() {
    # Modify selfhosted.sh to detect homelab.yaml
    # Add CLI commands: ./selfhosted.sh generate-from-homelab
    # Add validation: ./selfhosted.sh validate-homelab
    # Add migration: ./selfhosted.sh migrate-to-homelab
}
```

### 📅 Week 3: Migration and Testing

```bash
# Day 11-12: Simple migration tool
migrate_to_homelab_yaml() {
    echo "🔄 Migrating to homelab.yaml..."

    cat > homelab.yaml <<EOF
version: "2.0"
deployment: docker_compose

environment:
EOF

    # Environment from .env
    if [ -f .env ]; then
        grep "^[A-Z]" .env | sed 's/^/  /' >> homelab.yaml
    fi

    echo "" >> homelab.yaml
    echo "machines:" >> homelab.yaml
    echo "  driver: {host: localhost, user: $(whoami)}" >> homelab.yaml
    echo "" >> homelab.yaml
    echo "services:" >> homelab.yaml

    # Convert services.yaml to simple format
    if [ -f config/services.yaml ]; then
        yq '.services | to_entries[]' config/services.yaml | while read -r entry; do
            local service=$(echo "$entry" | yq '.key')
            local enabled=$(echo "$entry" | yq '.value.enabled')

            if [ "$enabled" = "true" ]; then
                local image=$(echo "$entry" | yq '.value.compose.image')
                echo "  $service:" >> homelab.yaml
                echo "    image: $image" >> homelab.yaml

                # Extract first port if any
                local port=$(echo "$entry" | yq '.value.compose.ports[0]? // empty' | sed 's/.*:\([0-9]*\)"/\1/')
                if [ -n "$port" ]; then
                    echo "    port: $port" >> homelab.yaml
                fi
            fi
        done
    fi

    echo "✅ Migration complete. Review homelab.yaml"
}

# Day 13-15: Testing and validation
test_simple_deployment() {
    # Test 1: Validate homelab.yaml
    ./scripts/validate_homelab_yaml.sh

    # Test 2: Generate bundles
    ./scripts/generate_bundles.sh

    # Test 3: Deploy to driver machine
    docker compose -f docker-compose-driver.yaml up -d

    # Test 4: Verify services are running
    check_service_health "homepage" "3000"
    check_service_health "actual" "5006"

    echo "✅ All tests passed"
}
```

## 4. File Structure

### 📁 New Files to Create

```bash
# Core implementation files
scripts/
├── validate_homelab_yaml.sh           # Simple validation
├── translate_homelab.sh               # homelab.yaml → deployment format
├── generate_bundles.sh                # Generate per-machine bundles
└── migrate_to_homelab.sh              # Migration from current format

# Configuration
homelab.yaml                            # New unified configuration file
homelab-example.yaml                   # Example configuration

# Generated files (examples)
generated-bundles/
├── driver/
│   ├── docker-compose-driver.yaml
│   └── nginx-driver.conf
└── node-01/
    ├── docker-compose-node-01.yaml
    └── nginx-node-01.conf
```

### 🔧 Modified Files

```bash
# Integration with existing system
selfhosted.sh                          # Add homelab.yaml support
scripts/service_generator.sh           # Support both old and new formats
scripts/common.sh                      # Add homelab.yaml functions
```

## 5. Implementation Functions

### 🛠️ Core Functions (Simplified)

```bash
# Main entry point
main() {
    local config_file="${1:-homelab.yaml}"

    if [ ! -f "$config_file" ]; then
        echo "❌ $config_file not found"
        exit 1
    fi

    # Validate
    validate_homelab_yaml "$config_file"

    # Generate bundles
    generate_all_bundles "$config_file"

    echo "✅ Generation complete"
}

# Simple validation
validate_homelab_yaml() {
    local config_file="$1"

    # Check required fields
    yq '.version' "$config_file" >/dev/null || { echo "❌ Missing version"; exit 1; }
    yq '.deployment' "$config_file" >/dev/null || { echo "❌ Missing deployment"; exit 1; }
    yq '.services' "$config_file" >/dev/null || { echo "❌ Missing services"; exit 1; }

    # Check each service has image
    yq '.services | to_entries[]' "$config_file" | while read -r entry; do
        local service=$(echo "$entry" | yq '.key')
        local image=$(echo "$entry" | yq '.value.image // empty')

        if [ -z "$image" ]; then
            echo "❌ Service $service missing image"
            exit 1
        fi
    done

    echo "✅ $config_file is valid"
}

# Bundle generation
generate_all_bundles() {
    local config_file="$1"
    local deployment_type=$(yq '.deployment' "$config_file")

    # Create output directory
    mkdir -p generated-bundles

    # Generate for each machine
    get_all_machines "$config_file" | while read -r machine; do
        local bundle_dir="generated-bundles/$machine"
        mkdir -p "$bundle_dir"

        echo "🔧 Generating $deployment_type bundle for $machine..."

        case "$deployment_type" in
            "docker_compose")
                translate_to_docker_compose "$machine" "$config_file" > "$bundle_dir/docker-compose.yaml"
                ;;
            "docker_swarm")
                translate_to_docker_swarm "$machine" "$config_file" > "$bundle_dir/docker-stack.yaml"
                ;;
        esac

        echo "✅ Generated bundle: $bundle_dir"
    done
}
```

## 6. Success Criteria

### 🎯 Simple Success Metrics

```yaml
success_criteria:
  ease_of_use:
    target: "Add new service in under 30 seconds"
    measurement: "Time from decision to deployed service"

  configuration_size:
    target: "homelab.yaml under 100 lines for typical homelab"
    current_baseline: "services.yaml + machines.yml + volumes.yaml ~300 lines"

  migration_time:
    target: "Migrate existing config in under 5 minutes"
    measurement: "Automated migration + manual review time"

  learning_curve:
    target: "New user can deploy homelab in 15 minutes"
    measurement: "From zero to working deployment"
```

### ✅ PoC Success Definition

```bash
# PoC is successful if:
poc_success() {
    # 1. Can add service in 3 lines
    echo "Adding new service..."
    cat >> homelab.yaml <<EOF
  new_service:
    image: nginx:alpine
    port: 8080
EOF

    # 2. Can generate valid docker-compose.yaml
    ./scripts/translate_homelab.sh > docker-compose-test.yaml
    docker compose -f docker-compose-test.yaml config >/dev/null

    # 3. Services deploy and work
    docker compose -f docker-compose-test.yaml up -d
    curl -f http://localhost:3000 >/dev/null  # homepage
    curl -f http://localhost:5006 >/dev/null  # actual
    curl -f http://localhost:8080 >/dev/null  # new_service

    echo "✅ PoC successful"
}
```

## 7. Timeline

### 📅 3-Week Implementation

```yaml
week_1:
  focus: "Basic translation engine"
  deliverables:
    - "homelab.yaml schema validation"
    - "Simple service translation"
    - "Basic machine assignment"
    - "PoC with 3 services working"

week_2:
  focus: "Multi-machine support"
  deliverables:
    - "Per-machine bundle generation"
    - "Machine assignment strategies"
    - "Integration with existing system"
    - "CLI command support"

week_3:
  focus: "Migration and testing"
  deliverables:
    - "Automated migration tool"
    - "Comprehensive testing"
    - "Documentation and examples"
    - "Production-ready implementation"
```

## 8. Examples

### 📝 Real Homelab Configuration

```yaml
# homelab.yaml - Real example
version: "2.0"
deployment: docker_compose

environment:
  BASE_DOMAIN: homelab.local
  PROJECT_ROOT: /opt/homelab

machines:
  driver: {host: 192.168.1.100, user: ubuntu}
  node-01: {host: 192.168.1.101, user: ubuntu}
  node-02: {host: 192.168.1.102, user: ubuntu}

services:
  # Infrastructure (deploys everywhere)
  nginx:
    image: nginx:alpine
    ports: [80, 443]
    deploy: all

  # Management (deploys to driver)
  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    port: 3000

  portainer:
    image: portainer/portainer-ce:latest
    port: 9000
    storage: true

  # Applications (specific deployment)
  actual:
    image: actualbudget/actual-server:latest
    port: 5006
    storage: true
    deploy: node-01

  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    port: 8123
    storage: 5GB
    deploy: node-02

  # Media (load balanced)
  jellyfin:
    image: jellyfin/jellyfin:latest
    port: 8096
    storage: 50GB
    deploy: random
```

### 🎯 Generated Output

```yaml
# docker-compose-driver.yaml (auto-generated)
version: '3.8'
services:
  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    restart: unless-stopped

  homepage:
    image: ghcr.io/gethomepage/homepage:latest
    ports: ["3000:3000"]
    restart: unless-stopped

  portainer:
    image: portainer/portainer-ce:latest
    ports: ["9000:9000"]
    volumes: ["./appdata/portainer:/data"]
    restart: unless-stopped
```

## 9. Conclusion

### ✅ Simple Implementation Approach

**Core Principle**: Make it trivial to add services.

**Key Implementation Points:**
1. **Single File**: Everything in `homelab.yaml`
2. **Minimal Validation**: Just check required fields
3. **Smart Translation**: Convert simple config to deployment format
4. **Machine Bundles**: Generate per-machine artifacts
5. **Easy Migration**: Automated conversion from current format

**Timeline**: 3 weeks to fully functional system.

**Success**: Adding a service is 2-3 lines, migration takes 5 minutes, new users deploy in 15 minutes.

This implementation plan prioritizes simplicity and user experience over technical complexity, making the homelab configuration as easy as possible while maintaining deployment flexibility.
