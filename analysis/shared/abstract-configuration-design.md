# Abstract Configuration Design

**Date**: 2025-01-08
**Purpose**: Design abstract service configuration interface with unified file structure
**Context**: Replace deployment-specific configuration with abstract interface supporting multiple deployment types

## Executive Summary

This document designs a new abstract configuration approach that separates universal service definitions from deployment-specific implementation details. The design includes a unified configuration file combining services, machines, and storage, with machine assignment strategies for focused deployment.

## 1. Abstract Configuration Schema

### 🎯 Core Abstract Service Schema

#### Universal Service Definition:
```yaml
# Abstract service schema
service_schema:
  name: "string"                    # Human-readable service name
  description: "string"             # Service description (optional)
  category: "string"                # Service category
  enabled: boolean                  # Enable/disable flag

  # Container definition (universal)
  container:
    image: "string"                 # Container image (without tag)
    tag: "string"                   # Image tag or version
    tag_strategy: "enum"            # latest, stable, version, custom

  # Abstract port definitions
  ports:
    port_name:
      internal: integer             # Container internal port
      protocol: "enum"              # http, https, tcp, udp
      public_access: boolean        # Should be accessible externally
      load_balancer: boolean        # Should be load balanced

  # Environment variables (abstract)
  environment:
    VAR_NAME: "value"              # Simple key-value pairs
    DOMAIN_VAR: "${SERVICE_DOMAIN}" # Variable substitution

  # Storage requirements (abstract)
  storage:
    volume_name:
      type: "enum"                  # application_data, cache, logs, media
      size: "string"                # 100MB, 1GB, 10GB
      mount_path: "string"          # Container mount path
      backup_priority: "enum"       # high, medium, low, none

  # Resource requirements (abstract)
  resources:
    cpu_min: float                  # Minimum CPU cores (0.1, 0.5, 1.0)
    cpu_max: float                  # Maximum CPU cores
    memory_min: "string"            # Minimum memory (128MB, 1GB)
    memory_max: "string"            # Maximum memory

  # Machine assignment
  machine_assignment:
    strategy: "enum"                # driver, random, specific, all, any
    machine_id: "string"            # Specific machine ID (if strategy=specific)
    constraints: []                 # Additional placement constraints

  # Health and monitoring
  health:
    check_url: "string"             # HTTP health check URL
    check_interval: "duration"      # 30s, 1m, 5m
    startup_timeout: "duration"     # Time to wait for startup

  # Dependencies
  dependencies:
    services: []                    # Required services
    external: []                    # External dependencies

  # Deployment overrides (optional)
  overrides:
    docker_compose: {}              # Docker Compose specific overrides
    docker_swarm: {}                # Docker Swarm specific overrides
    kubernetes: {}                  # Kubernetes specific overrides
```

### 🎯 Complete Unified Configuration Structure

#### unified.yaml Schema:
```yaml
# unified.yaml - Complete configuration schema
version: "2.0"
metadata:
  name: "homelab"
  description: "Home lab configuration"
  deployment_type: "docker_compose"  # compose, swarm, kubernetes

# Global defaults
defaults:
  domain_pattern: "${service}.${BASE_DOMAIN}"
  restart_policy: "unless-stopped"
  backup_schedule: "daily"
  log_retention: "30d"

# Infrastructure definition
infrastructure:
  driver:
    hostname: "string"
    ip: "string"
    user: "string"
    ssh_key: "string"               # SSH key path
    capabilities: []                # manager, worker, storage
    labels: {}                      # Custom labels

  machines:
    machine_id:
      hostname: "string"
      ip: "string"
      user: "string"
      ssh_key: "string"
      role: "enum"                  # manager, worker
      capabilities: []              # Available capabilities
      labels: {}                    # Machine labels
      hardware:                     # Optional hardware info
        cpu_cores: integer
        memory_gb: integer
        storage_gb: integer
        arch: "string"              # x86_64, arm64

# Storage configuration
storage:
  providers:
    local:
      enabled: boolean
      base_path: "string"
      permissions: "string"

    nfs:
      enabled: boolean
      server: "string"
      base_path: "string"
      mount_options: []

  volume_types:
    application_data:
      provider: "enum"              # local, nfs
      backup_enabled: boolean
      backup_schedule: "string"
      retention_policy: "string"

    cache:
      provider: "enum"
      backup_enabled: boolean

    logs:
      provider: "enum"
      backup_enabled: boolean
      retention_policy: "string"

# Network configuration
networks:
  default:
    driver: "bridge"
    subnet: "string"

  reverseproxy:
    driver: "bridge"
    external: true

# Service definitions
services:
  service_name:
    # Use abstract service schema defined above

# Global environment variables
environment:
  BASE_DOMAIN: "example.com"
  PROJECT_ROOT: "/opt/homelab"
  TIMEZONE: "UTC"
  PUID: 1000
  PGID: 1000
```

## 2. Machine Assignment Strategies

### 🎯 Assignment Strategy Definitions

#### Strategy Implementation:
```yaml
# Machine assignment strategies
strategies:
  driver:
    description: "Deploy to the driver machine only"
    implementation: "Single machine deployment to designated driver"
    use_cases:
      - "Development and testing"
      - "Single-node services"
      - "Management interfaces"
    example_services: ["homepage", "actual", "cryptpad"]

  random:
    description: "Deploy to one randomly selected machine"
    implementation: "Random selection from available machines"
    use_cases:
      - "Load distribution"
      - "Non-critical services"
      - "Stateless applications"
    example_services: ["monitoring_agent", "log_collector"]

  specific:
    description: "Deploy to specific machine by ID"
    implementation: "Direct assignment to named machine"
    configuration:
      machine_id: "node-01"
    use_cases:
      - "Hardware-specific services"
      - "Dedicated workloads"
      - "Storage-attached services"
    example_services: ["media_server", "database"]

  all:
    description: "Deploy to all machines"
    implementation: "Service deployed on every machine"
    use_cases:
      - "Infrastructure services"
      - "Reverse proxy"
      - "Monitoring agents"
    example_services: ["reverse_proxy", "monitoring", "log_agent"]

  any:
    description: "Deploy to any available machine"
    implementation: "Deployment system chooses optimal machine"
    use_cases:
      - "Flexible deployment"
      - "Resource optimization"
      - "High availability"
    example_services: ["api_services", "background_workers"]
```

### 🔧 Machine Assignment Logic

#### Assignment Resolution Algorithm:
```bash
# Machine assignment resolution
resolve_machine_assignment() {
    local service_key="$1"
    local strategy
    strategy=$(yq ".services[\"$service_key\"].machine_assignment.strategy" "$UNIFIED_CONFIG")

    case "$strategy" in
        "driver")
            echo "$(get_driver_machine)"
            ;;
        "random")
            echo "$(get_random_machine)"
            ;;
        "specific")
            local machine_id
            machine_id=$(yq ".services[\"$service_key\"].machine_assignment.machine_id" "$UNIFIED_CONFIG")
            echo "$machine_id"
            ;;
        "all")
            get_all_machines
            ;;
        "any")
            echo "any"  # Let deployment system decide
            ;;
        *)
            echo "driver"  # Default fallback
            ;;
    esac
}

# Machine list functions
get_driver_machine() {
    yq '.infrastructure.driver.hostname' "$UNIFIED_CONFIG"
}

get_all_machines() {
    {
        yq '.infrastructure.driver.hostname' "$UNIFIED_CONFIG"
        yq '.infrastructure.machines | keys[]' "$UNIFIED_CONFIG"
    } | sort -u
}

get_random_machine() {
    get_all_machines | shuf -n 1
}
```

## 3. Deployment-Specific Translation

### 🔄 Abstract to Docker Compose Translation

#### Translation Functions:
```bash
# Abstract service to Docker Compose translation
translate_to_docker_compose() {
    local service_key="$1"
    local target_machine="$2"

    echo "  $service_key:"

    # Translate container image
    translate_container_to_compose "$service_key"

    # Translate ports
    translate_ports_to_compose "$service_key"

    # Translate environment
    translate_environment_to_compose "$service_key"

    # Translate volumes
    translate_storage_to_compose "$service_key"

    # Translate resources (Docker Compose limits)
    translate_resources_to_compose "$service_key"

    # Apply overrides
    apply_compose_overrides "$service_key"
}

# Container translation
translate_container_to_compose() {
    local service_key="$1"

    local image
    image=$(yq ".services[\"$service_key\"].container.image" "$UNIFIED_CONFIG")
    local tag
    tag=$(yq ".services[\"$service_key\"].container.tag" "$UNIFIED_CONFIG")

    echo "    image: $image:$tag"
    echo "    restart: unless-stopped"  # From defaults
}

# Port translation
translate_ports_to_compose() {
    local service_key="$1"

    local ports
    ports=$(yq ".services[\"$service_key\"].ports | keys[]" "$UNIFIED_CONFIG")

    if [ -n "$ports" ]; then
        echo "    ports:"
        while read -r port_name; do
            local internal
            internal=$(yq ".services[\"$service_key\"].ports[\"$port_name\"].internal" "$UNIFIED_CONFIG")
            local public_access
            public_access=$(yq ".services[\"$service_key\"].ports[\"$port_name\"].public_access" "$UNIFIED_CONFIG")

            if [ "$public_access" = "true" ]; then
                echo "      - \"$internal:$internal\""
            fi
        done <<< "$ports"
    fi
}

# Environment translation
translate_environment_to_compose() {
    local service_key="$1"

    local env_vars
    env_vars=$(yq ".services[\"$service_key\"].environment | keys[]" "$UNIFIED_CONFIG")

    if [ -n "$env_vars" ]; then
        echo "    environment:"
        while read -r env_var; do
            local value
            value=$(yq ".services[\"$service_key\"].environment[\"$env_var\"]" "$UNIFIED_CONFIG")
            echo "      $env_var: $value"
        done <<< "$env_vars"
    fi
}
```

### 🔄 Abstract to Docker Swarm Translation

#### Swarm-Specific Translation:
```bash
# Abstract service to Docker Swarm translation
translate_to_docker_swarm() {
    local service_key="$1"

    echo "  $service_key:"

    # Basic container config (same as Compose)
    translate_container_to_compose "$service_key"

    # Swarm-specific deployment config
    translate_swarm_deployment "$service_key"

    # Swarm networks (overlay networks)
    translate_swarm_networks "$service_key"

    # Apply Swarm overrides
    apply_swarm_overrides "$service_key"
}

# Swarm deployment configuration
translate_swarm_deployment() {
    local service_key="$1"

    echo "    deploy:"

    # Machine assignment to placement constraints
    local strategy
    strategy=$(yq ".services[\"$service_key\"].machine_assignment.strategy" "$UNIFIED_CONFIG")

    case "$strategy" in
        "all")
            echo "      mode: global"
            ;;
        "specific")
            local machine_id
            machine_id=$(yq ".services[\"$service_key\"].machine_assignment.machine_id" "$UNIFIED_CONFIG")
            echo "      placement:"
            echo "        constraints:"
            echo "          - node.hostname == $machine_id"
            ;;
        *)
            echo "      mode: replicated"
            echo "      replicas: 1"
            ;;
    esac

    # Resource limits
    translate_swarm_resources "$service_key"
}
```

## 4. Per-Machine Artifact Generation

### 🎯 Machine-Specific Bundle Generation

#### Bundle Generation Strategy:
```bash
# Generate deployment bundles per machine
generate_machine_bundles() {
    local deployment_type="$1"  # compose, swarm, k8s

    # Get all machines
    local machines
    machines=$(get_all_machines)

    while read -r machine; do
        echo "🔧 Generating bundle for machine: $machine"
        generate_machine_bundle "$machine" "$deployment_type"
    done <<< "$machines"
}

# Generate bundle for specific machine
generate_machine_bundle() {
    local target_machine="$1"
    local deployment_type="$2"

    # Create machine-specific directory
    local bundle_dir="generated-bundles/$target_machine"
    mkdir -p "$bundle_dir"

    # Get services assigned to this machine
    local machine_services
    machine_services=$(get_services_for_machine "$target_machine")

    case "$deployment_type" in
        "compose")
            generate_docker_compose_bundle "$target_machine" "$machine_services" "$bundle_dir"
            ;;
        "swarm")
            generate_docker_swarm_bundle "$target_machine" "$machine_services" "$bundle_dir"
            ;;
    esac

    # Generate machine-specific nginx config
    generate_nginx_bundle "$target_machine" "$machine_services" "$bundle_dir"

    # Generate machine-specific domain variables
    generate_domains_bundle "$target_machine" "$machine_services" "$bundle_dir"
}

# Get services assigned to specific machine
get_services_for_machine() {
    local target_machine="$1"
    local assigned_services=""

    # Check each enabled service
    while read -r service_key; do
        local assigned_machines
        assigned_machines=$(resolve_machine_assignment "$service_key")

        if [[ "$assigned_machines" == *"$target_machine"* ]] || [[ "$assigned_machines" == "any" ]]; then
            assigned_services="$assigned_services $service_key"
        fi
    done < <(yq '.services | to_entries[] | select(.value.enabled == true) | .key' "$UNIFIED_CONFIG")

    echo "$assigned_services"
}
```

### 🌐 Reverse Proxy Distribution Strategy

#### Per-Machine Nginx Configuration:
```bash
# Generate nginx config for specific machine
generate_nginx_bundle() {
    local target_machine="$1"
    local machine_services="$2"
    local bundle_dir="$3"

    local nginx_dir="$bundle_dir/nginx"
    mkdir -p "$nginx_dir/conf.d"

    # Generate nginx.conf for this machine
    cat > "$nginx_dir/nginx.conf" <<EOF
# Nginx configuration for machine: $target_machine
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;

    # Include machine-specific service configurations
    include /etc/nginx/conf.d/*.conf;
}
EOF

    # Generate service-specific configurations
    for service in $machine_services; do
        generate_service_nginx_config "$service" "$target_machine" "$nginx_dir/conf.d"
    done
}

# Generate nginx config for specific service on specific machine
generate_service_nginx_config() {
    local service_key="$1"
    local target_machine="$2"
    local output_dir="$3"

    # Check if service has public web access
    local has_public_port
    has_public_port=$(yq ".services[\"$service_key\"].ports | to_entries[] | select(.value.public_access == true and .value.protocol == \"http\") | length" "$UNIFIED_CONFIG")

    if [ "$has_public_port" -gt 0 ]; then
        local service_domain="${service_key}.${BASE_DOMAIN}"
        local internal_port
        internal_port=$(yq ".services[\"$service_key\"].ports | to_entries[] | select(.value.public_access == true and .value.protocol == \"http\") | .value.internal" "$UNIFIED_CONFIG")

        cat > "$output_dir/$service_key.conf" <<EOF
# Nginx configuration for $service_key on $target_machine
server {
    listen 80;
    server_name $service_domain;

    location / {
        proxy_pass http://localhost:$internal_port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    fi
}
```

## 5. Migration Strategy

### 🔄 Backward Compatibility Approach

#### Migration Path:
```bash
# Migration from current format to unified format
migrate_current_to_unified() {
    echo "🔄 Migrating current configuration to unified format..."

    # Create backup
    backup_current_config

    # Convert services.yaml to unified format
    convert_services_yaml_to_unified

    # Convert machines.yml to unified format
    convert_machines_yml_to_unified

    # Convert volumes.yaml to unified format
    convert_volumes_yaml_to_unified

    # Validate unified configuration
    validate_unified_config

    echo "✅ Migration completed successfully"
}

# Convert current services.yaml
convert_services_yaml_to_unified() {
    local current_services="config/services.yaml"
    local temp_unified="unified-temp.yaml"

    # Start with unified template
    create_unified_template "$temp_unified"

    # Extract and convert each service
    while read -r service_key; do
        convert_service_to_abstract "$service_key" "$current_services" "$temp_unified"
    done < <(yq '.services | keys[]' "$current_services")
}

# Convert individual service from current to abstract format
convert_service_to_abstract() {
    local service_key="$1"
    local source_file="$2"
    local target_file="$3"

    # Extract current service definition
    local name
    name=$(yq ".services[\"$service_key\"].name" "$source_file")
    local enabled
    enabled=$(yq ".services[\"$service_key\"].enabled" "$source_file")

    # Convert compose configuration to abstract
    local image
    image=$(yq ".services[\"$service_key\"].compose.image" "$source_file")

    # Extract image name and tag
    local image_name="${image%:*}"
    local image_tag="${image##*:}"

    # Build abstract service definition
    yq eval ".services[\"$service_key\"].name = \"$name\"" -i "$target_file"
    yq eval ".services[\"$service_key\"].enabled = $enabled" -i "$target_file"
    yq eval ".services[\"$service_key\"].container.image = \"$image_name\"" -i "$target_file"
    yq eval ".services[\"$service_key\"].container.tag = \"$image_tag\"" -i "$target_file"

    # Set default machine assignment
    yq eval ".services[\"$service_key\"].machine_assignment.strategy = \"driver\"" -i "$target_file"

    echo "✅ Converted service: $service_key"
}
```

## 6. Implementation Timeline

### 🚧 Phase 1: Abstract Interface (2-3 weeks)
1. **Design Schema**: Finalize abstract service schema
2. **Create Translators**: Build abstract-to-deployment translators
3. **Proof of Concept**: Test with 2-3 services
4. **Validation**: Ensure translation accuracy

### 🚧 Phase 2: Unified Configuration (3-4 weeks)
1. **Design Unified Schema**: Complete unified.yaml structure
2. **Machine Assignment**: Implement assignment strategies
3. **Bundle Generation**: Create per-machine artifact generation
4. **Integration**: Integrate with existing generation pipeline

### 🚧 Phase 3: Migration and Testing (2-3 weeks)
1. **Migration Tools**: Create configuration migration utilities
2. **Backward Compatibility**: Support both formats during transition
3. **Comprehensive Testing**: Test all deployment scenarios
4. **Documentation**: Update all documentation

### 🚧 Phase 4: Deployment and Optimization (1-2 weeks)
1. **Production Deployment**: Deploy new configuration approach
2. **Performance Optimization**: Optimize generation performance
3. **User Feedback**: Gather and incorporate user feedback
4. **Final Documentation**: Complete user guides and examples

## 7. Conclusion

**✅ Design Complete**: Comprehensive abstract configuration design with unified file structure.

### Key Design Decisions

1. **Abstract Interface**: Universal service definitions with deployment-specific translation
2. **Unified Configuration**: Single file for services + machines + storage
3. **Machine Assignment**: Flexible strategies for service placement
4. **Bundle Generation**: Per-machine artifacts for improved isolation
5. **Migration Path**: Backward compatibility with current configuration

### Benefits Summary

- **Deployment Agnostic**: Services defined once, deployed anywhere
- **Simplified Management**: Single configuration file
- **Machine Awareness**: Services know where to deploy
- **Improved Isolation**: Machine-specific artifacts
- **Future-Proof**: Easy to add new deployment types

**Next Steps**: Implement proof-of-concept with 2-3 services to validate design before full implementation.
