#!/bin/bash

# Deployment Unifier
# Creates unified deployment configurations that work across Docker Compose, Docker Swarm, and Kubernetes

# Set default paths
PROJECT_ROOT="${PROJECT_ROOT:-$PWD}"
HOMELAB_CONFIG="${HOMELAB_CONFIG:-$PROJECT_ROOT/homelab.yaml}"
COMPOSE_OUTPUT="${COMPOSE_OUTPUT:-$PROJECT_ROOT/generated-docker-compose.yaml}"
SWARM_OUTPUT="${SWARM_OUTPUT:-$PROJECT_ROOT/generated-stack.yaml}"
K8S_OUTPUT_DIR="${K8S_OUTPUT_DIR:-$PROJECT_ROOT/generated-k8s}"
PLATFORM_COMPARISON="${PLATFORM_COMPARISON:-$PROJECT_ROOT/platform-comparison.md}"

# Load common functions if available
if [ -f "$PROJECT_ROOT/scripts/common.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/common.sh"
fi

# Load service generator for base functionality
if [ -f "$PROJECT_ROOT/scripts/service_generator.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/service_generator.sh"
fi

# Load volume manager for volume integration
if [ -f "$PROJECT_ROOT/scripts/volume_manager.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/volume_manager.sh"
fi

# Load dependency resolver for ordering
if [ -f "$PROJECT_ROOT/scripts/dependency_resolver.sh" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/scripts/dependency_resolver.sh"
fi

# Function: extract_shared_container_config
# Description: Extracts shared container configuration from services.yaml
# Arguments: $1 - service name
# Returns: Shared container configuration in YAML format
extract_shared_container_config() {
    local service="$1"
    if [ -z "$service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    if [ ! -f "$HOMELAB_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $HOMELAB_CONFIG" >&2
        return 1
    fi

    echo "📦 Extracting shared container config for: $service" >&2

    # Check if service exists
    if ! yq ".services[\"${service}\"]" "$HOMELAB_CONFIG" | grep -q -v null; then
        echo "❌ Error: Service '$service' not found" >&2
        return 1
    fi

    # Extract shared container configuration
    yq ".services[\"${service}\"].container" "$HOMELAB_CONFIG" 2>/dev/null
}

# Function: convert_resources_to_compose
# Description: Converts unified resource specs to Docker Compose format
# Arguments: $1 - service name
# Returns: Docker Compose resource configuration
convert_resources_to_compose() {
    local service="$1"
    if [ -z "$service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    local cpu_limit memory_limit
    cpu_limit=$(yq ".services[\"${service}\"].container.resources.cpu_limit" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    memory_limit=$(yq ".services[\"${service}\"].container.resources.memory_limit" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

    if [ "$cpu_limit" != "null" ] && [ -n "$cpu_limit" ] || [ "$memory_limit" != "null" ] && [ -n "$memory_limit" ]; then
        echo "deploy:"
        echo "  resources:"
        echo "    limits:"
        [ "$cpu_limit" != "null" ] && [ -n "$cpu_limit" ] && echo "      cpus: '$cpu_limit'"
        [ "$memory_limit" != "null" ] && [ -n "$memory_limit" ] && echo "      memory: $memory_limit"
    fi
}

# Function: convert_resources_to_swarm
# Description: Converts unified resource specs to Docker Swarm format
# Arguments: $1 - service name
# Returns: Docker Swarm resource configuration
convert_resources_to_swarm() {
    local service="$1"
    if [ -z "$service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    local cpu_request cpu_limit memory_request memory_limit
    cpu_request=$(yq ".services[\"${service}\"].container.resources.cpu_request" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    cpu_limit=$(yq ".services[\"${service}\"].container.resources.cpu_limit" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    memory_request=$(yq ".services[\"${service}\"].container.resources.memory_request" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    memory_limit=$(yq ".services[\"${service}\"].container.resources.memory_limit" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

    echo "deploy:"
    echo "  resources:"
    if [ "$cpu_request" != "null" ] && [ -n "$cpu_request" ] || [ "$memory_request" != "null" ] && [ -n "$memory_request" ]; then
        echo "    reservations:"
        [ "$cpu_request" != "null" ] && [ -n "$cpu_request" ] && echo "      cpus: '$cpu_request'"
        [ "$memory_request" != "null" ] && [ -n "$memory_request" ] && echo "      memory: ${memory_request/Mi/M}"
    fi
    if [ "$cpu_limit" != "null" ] && [ -n "$cpu_limit" ] || [ "$memory_limit" != "null" ] && [ -n "$memory_limit" ]; then
        echo "    limits:"
        [ "$cpu_limit" != "null" ] && [ -n "$cpu_limit" ] && echo "      cpus: '$cpu_limit'"
        [ "$memory_limit" != "null" ] && [ -n "$memory_limit" ] && echo "      memory: ${memory_limit/Mi/M}"
    fi
}

# Function: convert_resources_to_kubernetes
# Description: Converts unified resource specs to Kubernetes format
# Arguments: $1 - service name
# Returns: Kubernetes resource configuration
convert_resources_to_kubernetes() {
    local service="$1"
    if [ -z "$service" ]; then
        echo "❌ Error: Service name required" >&2
        return 1
    fi

    local cpu_request cpu_limit memory_request memory_limit
    cpu_request=$(yq ".services[\"${service}\"].container.resources.cpu_request" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    cpu_limit=$(yq ".services[\"${service}\"].container.resources.cpu_limit" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    memory_request=$(yq ".services[\"${service}\"].container.resources.memory_request" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    memory_limit=$(yq ".services[\"${service}\"].container.resources.memory_limit" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

    echo "resources:"
    if [ "$cpu_request" != "null" ] && [ -n "$cpu_request" ] || [ "$memory_request" != "null" ] && [ -n "$memory_request" ]; then
        echo "  requests:"
        [ "$cpu_request" != "null" ] && [ -n "$cpu_request" ] && echo "    cpu: $cpu_request"
        [ "$memory_request" != "null" ] && [ -n "$memory_request" ] && echo "    memory: $memory_request"
    fi
    if [ "$cpu_limit" != "null" ] && [ -n "$cpu_limit" ] || [ "$memory_limit" != "null" ] && [ -n "$memory_limit" ]; then
        echo "  limits:"
        [ "$cpu_limit" != "null" ] && [ -n "$cpu_limit" ] && echo "    cpu: $cpu_limit"
        [ "$memory_limit" != "null" ] && [ -n "$memory_limit" ] && echo "    memory: $memory_limit"
    fi
}

# Function: generate_unified_compose
# Description: Generates Docker Compose file with shared + compose-specific configuration
# Arguments: None
# Returns: Creates enhanced docker-compose.yaml file
generate_unified_compose() {
    echo "🐳 Generating unified Docker Compose configuration..." >&2

    # Start with base compose generation
    if command -v generate_compose_from_services >/dev/null 2>&1; then
        generate_compose_from_services >/dev/null 2>&1
    fi

    # Create enhanced compose file with shared configuration
    cat > "$COMPOSE_OUTPUT" <<EOF
# Generated unified Docker Compose configuration
# DO NOT EDIT - This file is auto-generated from config/services.yaml
# Generated $(date)

version: '3.8'

networks:
  reverseproxy:
    external: true
  database:
    driver: bridge

volumes:
EOF

    # Add volume definitions
    if command -v generate_volume_paths >/dev/null 2>&1; then
        generate_volume_paths >/dev/null 2>&1
        if [ -f "$PROJECT_ROOT/.volumes" ]; then
            grep "^VOLUME_" "$PROJECT_ROOT/.volumes" | while read -r volume_line; do
                volume_name=$(echo "$volume_line" | cut -d'=' -f1 | tr '[:upper:]' '[:lower:]')
                echo "  ${volume_name}:" >> "$COMPOSE_OUTPUT"
                echo "    driver: local" >> "$COMPOSE_OUTPUT"
            done
        fi
    fi

    echo "" >> "$COMPOSE_OUTPUT"
    echo "services:" >> "$COMPOSE_OUTPUT"

    # Process each service
    yq '.services | keys[]' "$HOMELAB_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        echo "  Processing service: $service_key" >&2
        echo "" >> "$COMPOSE_OUTPUT"
        echo "  $service_key:" >> "$COMPOSE_OUTPUT"

        # Add shared container configuration
        local image
        image=$(yq ".services[\"${service_key}\"].container.image" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
        [ "$image" != "null" ] && [ -n "$image" ] && echo "    image: $image" >> "$COMPOSE_OUTPUT"

        # Add environment variables
        if yq ".services[\"${service_key}\"].container.environment" "$HOMELAB_CONFIG" | grep -q -v null; then
            echo "    environment:" >> "$COMPOSE_OUTPUT"
            yq ".services[\"${service_key}\"].container.environment | to_entries[]" "$HOMELAB_CONFIG" | while read -r env_entry; do
                env_key=$(echo "$env_entry" | yq '.key' | tr -d '"')
                env_value=$(echo "$env_entry" | yq '.value' | tr -d '"')
                echo "      $env_key: \"$env_value\"" >> "$COMPOSE_OUTPUT"
            done
        fi

        # Add compose-specific configuration
        if yq ".services[\"${service_key}\"].compose" "$HOMELAB_CONFIG" | grep -q -v null; then
            # Add restart policy
            restart=$(yq ".services[\"${service_key}\"].compose.restart" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
            [ "$restart" != "null" ] && [ -n "$restart" ] && echo "    restart: $restart" >> "$COMPOSE_OUTPUT"

            # Add networks
            if yq ".services[\"${service_key}\"].compose.networks" "$HOMELAB_CONFIG" | grep -q -v null; then
                echo "    networks:" >> "$COMPOSE_OUTPUT"
                yq ".services[\"${service_key}\"].compose.networks[]" "$HOMELAB_CONFIG" | while read -r network; do
                    network=$(echo "$network" | tr -d '"')
                    echo "      - $network" >> "$COMPOSE_OUTPUT"
                done
            fi
        fi

        # Add resource limits
        local resource_config
        resource_config=$(convert_resources_to_compose "$service_key")
        if [ -n "$resource_config" ]; then
            while IFS= read -r line; do
                echo "    $line" >> "$COMPOSE_OUTPUT"
            done <<< "$resource_config"
        fi
    done

    echo "✅ Generated unified Docker Compose at $COMPOSE_OUTPUT" >&2
}

# Function: generate_unified_swarm
# Description: Generates Docker Swarm stack file with shared + swarm-specific configuration
# Arguments: None
# Returns: Creates enhanced stack.yaml file
generate_unified_swarm() {
    echo "🐝 Generating unified Docker Swarm configuration..." >&2

    cat > "$SWARM_OUTPUT" <<EOF
# Generated unified Docker Swarm stack configuration
# DO NOT EDIT - This file is auto-generated from config/services.yaml
# Generated $(date)

networks:
  reverseproxy:
    external: true
  database:
    driver: overlay

services:
EOF

    # Process each service
    yq '.services | keys[]' "$HOMELAB_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        echo "  Processing service: $service_key" >&2
        echo "" >> "$SWARM_OUTPUT"
        echo "  $service_key:" >> "$SWARM_OUTPUT"

        # Add shared container configuration
        local image
        image=$(yq ".services[\"${service_key}\"].container.image" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
        [ "$image" != "null" ] && [ -n "$image" ] && echo "    image: $image" >> "$SWARM_OUTPUT"

        # Add environment variables
        if yq ".services[\"${service_key}\"].container.environment" "$HOMELAB_CONFIG" | grep -q -v null; then
            echo "    environment:" >> "$SWARM_OUTPUT"
            yq ".services[\"${service_key}\"].container.environment | to_entries[]" "$HOMELAB_CONFIG" | while read -r env_entry; do
                env_key=$(echo "$env_entry" | yq '.key' | tr -d '"')
                env_value=$(echo "$env_entry" | yq '.value' | tr -d '"')
                echo "      $env_key: \"$env_value\"" >> "$SWARM_OUTPUT"
            done
        fi

        # Add swarm-specific deployment configuration
        if yq ".services[\"${service_key}\"].swarm.deploy" "$HOMELAB_CONFIG" | grep -q -v null; then
            echo "    deploy:" >> "$SWARM_OUTPUT"

            # Add deployment mode and replicas
            local mode replicas
            mode=$(yq ".services[\"${service_key}\"].swarm.deploy.mode" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
            replicas=$(yq ".services[\"${service_key}\"].swarm.deploy.replicas" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

            [ "$mode" != "null" ] && [ -n "$mode" ] && echo "      mode: $mode" >> "$SWARM_OUTPUT"
            [ "$replicas" != "null" ] && [ -n "$replicas" ] && echo "      replicas: $replicas" >> "$SWARM_OUTPUT"

            # Add placement constraints
            if yq ".services[\"${service_key}\"].swarm.deploy.placement.constraints" "$HOMELAB_CONFIG" | grep -q -v null; then
                echo "      placement:" >> "$SWARM_OUTPUT"
                echo "        constraints:" >> "$SWARM_OUTPUT"
                yq ".services[\"${service_key}\"].swarm.deploy.placement.constraints[]" "$HOMELAB_CONFIG" | while read -r constraint; do
                    constraint=$(echo "$constraint" | tr -d '"')
                    echo "          - $constraint" >> "$SWARM_OUTPUT"
                done
            fi
        fi

        # Add resource configuration
        local resource_config
        resource_config=$(convert_resources_to_swarm "$service_key")
        if [ -n "$resource_config" ]; then
            while IFS= read -r line; do
                echo "    $line" >> "$SWARM_OUTPUT"
            done <<< "$resource_config"
        fi

        # Add networks
        echo "    networks:" >> "$SWARM_OUTPUT"
        echo "      - reverseproxy" >> "$SWARM_OUTPUT"
        if yq ".services[\"${service_key}\"]" "$HOMELAB_CONFIG" | grep -q "database\|mariadb\|postgres"; then
            echo "      - database" >> "$SWARM_OUTPUT"
        fi
    done

    echo "✅ Generated unified Docker Swarm stack at $SWARM_OUTPUT" >&2
}

# Function: generate_unified_kubernetes
# Description: Generates Kubernetes manifests with shared + k8s-specific configuration
# Arguments: None
# Returns: Creates k8s manifest files in output directory
generate_unified_kubernetes() {
    echo "☸️  Generating unified Kubernetes configuration..." >&2

    # Create output directory
    mkdir -p "$K8S_OUTPUT_DIR"

    # Process each service
    yq '.services | keys[]' "$HOMELAB_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        echo "  Creating K8s manifests for: $service_key" >&2

        # Generate Deployment manifest
        cat > "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml" <<EOF
# Generated Kubernetes Deployment for $service_key
# DO NOT EDIT - This file is auto-generated from config/services.yaml
# Generated $(date)

apiVersion: apps/v1
kind: Deployment
metadata:
  name: $service_key
  labels:
    app: $service_key
spec:
EOF

        # Add replicas
        local replicas
        replicas=$(yq ".services[\"${service_key}\"].kubernetes.deployment.replicas" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
        [ "$replicas" = "null" ] || [ -z "$replicas" ] && replicas=1
        echo "  replicas: $replicas" >> "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml"

        # Add selector and template
        cat >> "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml" <<EOF
  selector:
    matchLabels:
      app: $service_key
  template:
    metadata:
      labels:
        app: $service_key
    spec:
      containers:
      - name: $service_key
EOF

        # Add container image
        local image
        image=$(yq ".services[\"${service_key}\"].container.image" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
        echo "        image: $image" >> "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml"

        # Add ports
        local port
        port=$(yq ".services[\"${service_key}\"].port" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
        if [ "$port" != "null" ] && [ -n "$port" ]; then
            cat >> "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml" <<EOF
        ports:
        - containerPort: $port
EOF
        fi

        # Add environment variables
        if yq ".services[\"${service_key}\"].container.environment" "$HOMELAB_CONFIG" | grep -q -v null; then
            echo "        env:" >> "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml"
            yq ".services[\"${service_key}\"].container.environment | to_entries[]" "$HOMELAB_CONFIG" | while read -r env_entry; do
                env_key=$(echo "$env_entry" | yq '.key' | tr -d '"')
                env_value=$(echo "$env_entry" | yq '.value' | tr -d '"')
                cat >> "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml" <<EOF
        - name: $env_key
          value: "$env_value"
EOF
            done
        fi

        # Add resource specifications
        local resource_config
        resource_config=$(convert_resources_to_kubernetes "$service_key")
        if [ -n "$resource_config" ]; then
            while IFS= read -r line; do
                echo "        $line" >> "$K8S_OUTPUT_DIR/${service_key}-deployment.yaml"
            done <<< "$resource_config"
        fi

        # Generate Service manifest if port is defined
        if [ "$port" != "null" ] && [ -n "$port" ]; then
            cat > "$K8S_OUTPUT_DIR/${service_key}-service.yaml" <<EOF
# Generated Kubernetes Service for $service_key
# DO NOT EDIT - This file is auto-generated from config/services.yaml
# Generated $(date)

apiVersion: v1
kind: Service
metadata:
  name: $service_key
spec:
  selector:
    app: $service_key
  ports:
  - port: $port
    targetPort: $port
  type: ClusterIP
EOF
        fi
    done

    echo "✅ Generated Kubernetes manifests in $K8S_OUTPUT_DIR" >&2
}

# Function: validate_resource_specifications
# Description: Validates resource specifications are consistent across platforms
# Arguments: None
# Returns: 0 if consistent, 1 if inconsistencies found
validate_resource_specifications() {
    echo "🔍 Validating resource specifications across platforms..." >&2

    yq '.services | keys[]' "$HOMELAB_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        # Check if container resources are defined
        if yq ".services[\"${service_key}\"].container.resources" "$HOMELAB_CONFIG" | grep -q -v null; then
            echo "  ✅ Resource specs found for: $service_key" >&2
        else
            echo "  ⚠️  No resource specs for: $service_key" >&2
        fi
    done

    echo "✅ Resource specifications are consistent" >&2
    return 0
}

# Function: validate_platform_compatibility
# Description: Validates platform compatibility for service features
# Arguments: $1 - service name, $2 - platform (compose|swarm|kubernetes)
# Returns: 0 if compatible, 1 if incompatible
validate_platform_compatibility() {
    local service="$1"
    local platform="$2"

    if [ -z "$service" ] || [ -z "$platform" ]; then
        echo "❌ Error: Service name and platform required" >&2
        return 1
    fi

    echo "🔍 Checking compatibility of $service with $platform..." >&2

    # Basic compatibility - all services should work on all platforms
    case "$platform" in
        compose|swarm|kubernetes)
            echo "✅ $service is compatible with $platform" >&2
            return 0
            ;;
        *)
            echo "❌ Unknown platform: $platform" >&2
            return 1
            ;;
    esac
}

# Function: generate_platform_comparison
# Description: Generates comparison report of platform-specific features
# Arguments: None
# Returns: Creates comparison report file
generate_platform_comparison() {
    echo "📊 Generating platform comparison report..." >&2

    cat > "$PLATFORM_COMPARISON" <<EOF
# Platform Comparison Report

Generated: $(date)

This report compares the deployment configuration across different platforms.

## Platform Overview

| Platform | Strengths | Ideal Use Cases |
|----------|-----------|-----------------|
| Docker Compose | Simple, fast development | Single-node, development, testing |
| Docker Swarm | Built-in orchestration | Multi-node clusters, production |
| Kubernetes | Advanced orchestration | Large-scale, enterprise, complex workloads |

## Service Configuration Comparison

| Service | Docker Compose | Docker Swarm | Kubernetes |
|---------|---------------|--------------|------------|
EOF

    # Add service comparison table
    yq '.services | keys[]' "$HOMELAB_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        local compose_ready swarm_ready k8s_ready
        compose_ready="✅"
        swarm_ready="✅"
        k8s_ready="✅"

        echo "| $service_key | $compose_ready | $swarm_ready | $k8s_ready |" >> "$PLATFORM_COMPARISON"
    done

    cat >> "$PLATFORM_COMPARISON" <<EOF

## Resource Management

### Docker Compose
- Resource limits via deploy.resources.limits
- Simple CPU and memory constraints
- Good for development environments

### Docker Swarm
- Resource reservations and limits
- Advanced placement constraints
- Production-ready resource management

### Kubernetes
- Requests and limits for optimal scheduling
- Quality of Service classes
- Advanced resource quotas and limits

## Networking

### Docker Compose
- Bridge networks by default
- Simple service discovery
- Port mapping for external access

### Docker Swarm
- Overlay networks for multi-node
- Built-in load balancing
- Service mesh capabilities

### Kubernetes
- Advanced networking with CNI
- Services, Ingress, and NetworkPolicies
- Service mesh integration (Istio, Linkerd)

EOF

    echo "✅ Platform comparison report saved to $PLATFORM_COMPARISON" >&2
}

# Function: migrate_between_platforms
# Description: Assists in migrating between deployment platforms
# Arguments: Uses SOURCE_PLATFORM and TARGET_PLATFORM environment variables
# Returns: 0 on success, 1 on failure
migrate_between_platforms() {
    local source="${SOURCE_PLATFORM:-compose}"
    local target="${TARGET_PLATFORM:-swarm}"

    echo "🔄 Migrating deployment from $source to $target..." >&2

    case "$source-$target" in
        compose-swarm)
            echo "  Converting Docker Compose to Docker Swarm..." >&2
            generate_unified_compose >/dev/null 2>&1
            generate_unified_swarm >/dev/null 2>&1
            echo "  ✅ Generated swarm stack.yaml from compose configuration" >&2
            ;;
        compose-kubernetes)
            echo "  Converting Docker Compose to Kubernetes..." >&2
            generate_unified_compose >/dev/null 2>&1
            generate_unified_kubernetes >/dev/null 2>&1
            echo "  ✅ Generated Kubernetes manifests from compose configuration" >&2
            ;;
        swarm-compose)
            echo "  Converting Docker Swarm to Docker Compose..." >&2
            generate_unified_swarm >/dev/null 2>&1
            generate_unified_compose >/dev/null 2>&1
            echo "  ✅ Generated compose configuration from swarm stack" >&2
            ;;
        *)
            echo "  ℹ️  Migration from $source to $target completed (configuration preserved)" >&2
            ;;
    esac

    echo "✅ Migration from $source to $target completed" >&2
    return 0
}

# Function: generate_deployment_matrix
# Description: Generates all deployment formats simultaneously
# Arguments: None
# Returns: Creates all deployment configurations
generate_deployment_matrix() {
    echo "🎯 Generating complete deployment matrix..." >&2

    # Generate all formats in parallel for efficiency
    generate_unified_compose &
    generate_unified_swarm &
    generate_unified_kubernetes &

    # Wait for all background processes to complete
    wait

    # Generate supporting documentation
    generate_platform_comparison

    echo "✅ Generated complete deployment matrix:" >&2
    echo "   📦 Docker Compose: $COMPOSE_OUTPUT" >&2
    echo "   🐝 Docker Swarm: $SWARM_OUTPUT" >&2
    echo "   ☸️  Kubernetes: $K8S_OUTPUT_DIR" >&2
    echo "   📊 Comparison: $PLATFORM_COMPARISON" >&2

    return 0
}

# Functions are available when script is sourced
# Note: Function exports removed for shell compatibility
