#!/bin/bash

# Docker Compose Translation Engine
# Translates homelab.yaml to Docker Compose configurations for distributed deployment
# Part of Issue #35 - Docker Compose Translation Engine

set -e

# Get script directory for relative path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Default configuration
HOMELAB_CONFIG="${HOMELAB_CONFIG:-$PROJECT_ROOT/homelab.yaml}"
OUTPUT_DIR="${OUTPUT_DIR:-$PROJECT_ROOT/generated/docker-compose}"

# Logging functions
log_info() {
    echo "ℹ️  $*"
}

log_success() {
    echo "✅ $*"
}

log_error() {
    echo "❌ $*" >&2
}

log_warning() {
    echo "⚠️  $*"
}

# Function: validate_homelab_config_compose
# Description: Validates that homelab.yaml exists and has correct deployment type for Compose
# Arguments: None
# Returns: 0 on success, 1 on failure
validate_homelab_config_compose() {
    log_info "Validating homelab.yaml configuration..."

    if [[ ! -f "$HOMELAB_CONFIG" ]]; then
        log_error "homelab.yaml not found at: $HOMELAB_CONFIG"
        return 1
    fi

    # Check deployment type
    local deployment_type
    deployment_type=$(yq '.deployment' "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

    if [[ "$deployment_type" != "docker_compose" ]]; then
        log_error "Invalid deployment type: '$deployment_type'. Expected 'docker_compose'"
        return 1
    fi

    log_success "homelab.yaml validation passed"
    return 0
}

# Function: get_machine_list
# Description: Extracts machine names from homelab.yaml
# Arguments: None
# Returns: List of machine names (one per line)
get_machine_list() {
    yq '.machines | keys | .[]' "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"'
}

# Function: get_services_for_machine
# Description: Gets services that should be deployed on a specific machine
# Arguments: $1 - machine name
# Returns: List of service names (one per line)
get_services_for_machine() {
    local machine_name="$1"

    # Get all services
    local all_services
    all_services=$(yq '.services | keys | .[]' "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

    while IFS= read -r service; do
        [[ -z "$service" ]] && continue

        # Check if service is enabled (handle both boolean and string values)
        local enabled
        enabled=$(yq ".services[\"$service\"].enabled" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
        # Default to true if enabled field is missing or null
        [[ "$enabled" == "null" || -z "$enabled" ]] && enabled="true"
        [[ "$enabled" != "true" ]] && continue

        # Check deployment strategy
        local deploy_strategy
        deploy_strategy=$(yq ".services[\"$service\"].deploy // \"any\"" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

        case "$deploy_strategy" in
            "all")
                echo "$service"
                ;;
            "driver")
                # Deploy on first machine (driver)
                local first_machine
                first_machine=$(get_machine_list | head -n1)
                if [[ "$machine_name" == "$first_machine" ]]; then
                    echo "$service"
                fi
                ;;
            "any"|"random")
                # For simplicity, deploy on first machine for "any" and "random"
                local first_machine
                first_machine=$(get_machine_list | head -n1)
                if [[ "$machine_name" == "$first_machine" ]]; then
                    echo "$service"
                fi
                ;;
            "$machine_name")
                # Deploy on specific machine
                echo "$service"
                ;;
        esac
    done <<< "$all_services"

    # Ensure function always returns 0
    return 0
}

# Function: generate_docker_compose_for_machine
# Description: Generates docker-compose.yaml for a specific machine
# Arguments: $1 - machine name
# Returns: 0 on success, 1 on failure
generate_docker_compose_for_machine() {
    local machine_name="$1"
    local machine_output_dir="$OUTPUT_DIR/$machine_name"
    local compose_file="$machine_output_dir/docker-compose.yaml"

    log_info "Generating Docker Compose for machine: $machine_name"

    # Create output directory
    mkdir -p "$machine_output_dir"

    # Get services for this machine
    local services
    services=$(get_services_for_machine "$machine_name")

    if [[ -z "$services" ]]; then
        log_warning "No services assigned to machine: $machine_name"
        return 0
    fi

    # Start docker-compose.yaml file
    cat > "$compose_file" <<EOF
# Generated Docker Compose for machine: $machine_name
# Source: homelab.yaml
# DO NOT EDIT - This file is auto-generated
# Generated: $(date)

version: '3.8'

services:
EOF

    # Add reverse proxy (nginx) service for this machine
    cat >> "$compose_file" <<EOF
  # Reverse Proxy for local services
  nginx-proxy:
    image: nginx:alpine
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./ssl:/etc/nginx/ssl:ro
    networks:
      - homelab
    restart: unless-stopped

EOF

    # Add each service for this machine
    while IFS= read -r service; do
        [[ -z "$service" ]] && continue

        # Skip nginx service as we add nginx-proxy separately
        [[ "$service" == "nginx" ]] && continue

        log_info "  Adding service: $service"

        # Get service configuration
        local image port storage
        image=$(yq ".services[\"$service\"].image" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
        port=$(yq ".services[\"$service\"].port" "$HOMELAB_CONFIG" 2>/dev/null)
        storage=$(yq ".services[\"$service\"].storage // false" "$HOMELAB_CONFIG" 2>/dev/null)

        # Start service definition
        cat >> "$compose_file" <<EOF
  # Service: $service
  $service:
    image: $image
    container_name: $service
EOF

        # Add port mapping (only if not conflicting with nginx and port is valid)
        if [[ "$port" != "null" && "$port" != "80" && "$port" != "443" ]]; then
            cat >> "$compose_file" <<EOF
    ports:
      - "$port:$port"
EOF
        elif [[ "$port" == "80" || "$port" == "443" ]]; then
            # Expose port for nginx reverse proxy
            cat >> "$compose_file" <<EOF
    expose:
      - "$port"
EOF
        fi

        # Add storage if needed
        if [[ "$storage" == "true" ]] || [[ "$storage" =~ ^[0-9]+[GMT]B$ ]]; then
            cat >> "$compose_file" <<EOF
    volumes:
      - ${service}_data:/data
EOF
        fi

        # Add environment variables
        local env_vars
        env_vars=$(yq ".services[\"$service\"].environment // {}" "$HOMELAB_CONFIG" 2>/dev/null)

        if [[ "$env_vars" != "{}" && "$env_vars" != "null" ]]; then
            cat >> "$compose_file" <<EOF
    environment:
EOF
            # Add environment variables
            yq ".services[\"$service\"].environment | to_entries | .[] | \"      - \" + .key + \"=\" + (.value | tostring)" "$HOMELAB_CONFIG" 2>/dev/null >> "$compose_file"
        fi

        # Add to homelab network
        cat >> "$compose_file" <<EOF
    networks:
      - homelab
    restart: unless-stopped

EOF
    done <<< "$services"

    # Add networks section
    cat >> "$compose_file" <<EOF
networks:
  homelab:
    driver: bridge
EOF

    # Add volumes section if needed
    local has_volumes=false
    while IFS= read -r service; do
        [[ -z "$service" ]] && continue
        local storage
        storage=$(yq ".services[\"$service\"].storage // false" "$HOMELAB_CONFIG" 2>/dev/null)
        if [[ "$storage" == "true" ]] || [[ "$storage" =~ ^[0-9]+[GMT]B$ ]]; then
            if [[ "$has_volumes" == "false" ]]; then
                echo "" >> "$compose_file"
                echo "volumes:" >> "$compose_file"
                has_volumes=true
            fi
            echo "  ${service}_data:" >> "$compose_file"
        fi
    done <<< "$services"

    log_success "Generated Docker Compose for $machine_name at: $compose_file"
    return 0
}

# Function: generate_nginx_config_for_machine
# Description: Generates nginx configuration for a specific machine
# Arguments: $1 - machine name
# Returns: 0 on success, 1 on failure
generate_nginx_config_for_machine() {
    local machine_name="$1"
    local machine_output_dir="$OUTPUT_DIR/$machine_name"
    local nginx_dir="$machine_output_dir/nginx"

    log_info "Generating nginx configuration for machine: $machine_name"

    # Create nginx directory structure
    mkdir -p "$nginx_dir/conf.d"

    # Get services for this machine
    local services
    services=$(get_services_for_machine "$machine_name")

    # Generate main nginx.conf
    cat > "$nginx_dir/nginx.conf" <<EOF
# Generated nginx configuration for machine: $machine_name
# Source: homelab.yaml
# DO NOT EDIT - This file is auto-generated
# Generated: $(date)

events {
    worker_connections 1024;
}

http {
    include       mime.types;
    default_type  application/octet-stream;

    # Logging
    log_format main '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                    '\$status \$body_bytes_sent "\$http_referer" '
                    '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Basic settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # Health check endpoint
    server {
        listen 80 default_server;
        server_name _;

        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }

    # Include service configurations
    include conf.d/*.conf;
}
EOF

    # Get base domain for service URLs
    local base_domain
    base_domain=$(get_base_domain "$HOMELAB_CONFIG")

    # Generate configuration for each service that needs reverse proxy
    while IFS= read -r service; do
        [[ -z "$service" ]] && continue

                # Check if this is a web service that needs nginx proxy
        if is_web_service "$service" "$HOMELAB_CONFIG"; then
            local port
            port=$(yq ".services[\"$service\"].port" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

            # Skip if no port (can't proxy without knowing the port)
            if [[ -z "$port" || "$port" == "null" ]]; then
                log_info "  Skipping nginx config for $service: no port specified"
                continue
            fi

            # Get custom domain or use default pattern
            local service_domain
            service_domain=$(yq ".services[\"$service\"].domain // \"${service}.${base_domain}\"" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

            log_info "  Creating nginx config for: $service (${service_domain})"

            cat > "$nginx_dir/conf.d/${service}.conf" <<EOF
# Service: $service
server {
    listen 80;
    server_name ${service_domain};

    location / {
        proxy_pass http://$service:$port;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
        fi
    done <<< "$services"

    log_success "Generated nginx configuration for $machine_name"
    return 0
}

# Function: generate_deployment_script_for_machine
# Description: Generates deployment script for a specific machine
# Arguments: $1 - machine name
# Returns: 0 on success, 1 on failure
generate_deployment_script_for_machine() {
    local machine_name="$1"
    local machine_output_dir="$OUTPUT_DIR/$machine_name"
    local deploy_script="$machine_output_dir/deploy.sh"

    log_info "Generating deployment script for machine: $machine_name"

    # Ensure directory exists
    mkdir -p "$machine_output_dir"

    # Get machine configuration
    local machine_host machine_user
    machine_host=$(yq ".machines[\"$machine_name\"].host" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')
    machine_user=$(yq ".machines[\"$machine_name\"].user" "$HOMELAB_CONFIG" 2>/dev/null | tr -d '"')

    cat > "$deploy_script" <<EOF
#!/bin/bash
# Deployment script for machine: $machine_name
# Host: $machine_host
# User: $machine_user
# Generated: $(date)

set -e

MACHINE_NAME="$machine_name"
MACHINE_HOST="$machine_host"
MACHINE_USER="$machine_user"
LOCAL_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Deploying to \$MACHINE_NAME (\$MACHINE_HOST)..."

# Function to run commands on remote machine
remote_exec() {
    ssh "\$MACHINE_USER@\$MACHINE_HOST" "\$@"
}

# Function to copy files to remote machine
remote_copy() {
    local src="\$1"
    local dest="\$2"
    scp -r "\$src" "\$MACHINE_USER@\$MACHINE_HOST:\$dest"
}

# Create remote directory
echo "📁 Creating remote directory..."
remote_exec "mkdir -p ~/homelab"

# Copy docker-compose.yaml and configs
echo "📤 Copying configuration files..."
remote_copy "\$LOCAL_DIR/docker-compose.yaml" "~/homelab/"
remote_copy "\$LOCAL_DIR/nginx/" "~/homelab/"

# Deploy services
echo "🐳 Deploying Docker Compose services..."
remote_exec "cd ~/homelab && docker compose down --remove-orphans"
remote_exec "cd ~/homelab && docker compose pull"
remote_exec "cd ~/homelab && docker compose up -d"

# Show status
echo "📊 Deployment status:"
remote_exec "cd ~/homelab && docker compose ps"

echo "✅ Deployment to \$MACHINE_NAME completed successfully!"
EOF

    chmod +x "$deploy_script"

    log_success "Generated deployment script for $machine_name"
    return 0
}

# Function: translate_homelab_to_compose
# Description: Main function to translate homelab.yaml to Docker Compose configurations
# Arguments: None
# Returns: 0 on success, 1 on failure
translate_homelab_to_compose() {
    log_info "Starting homelab.yaml to Docker Compose translation..."

    # Validate configuration
    validate_homelab_config_compose || return 1

    # Create output directory
    mkdir -p "$OUTPUT_DIR"

    # Get all machines
    local machines
    machines=$(get_machine_list)

    if [[ -z "$machines" ]]; then
        log_error "No machines defined in homelab.yaml"
        return 1
    fi

    # Generate configurations for each machine
    while IFS= read -r machine; do
        [[ -z "$machine" ]] && continue

        log_info "Processing machine: $machine"
        generate_docker_compose_for_machine "$machine" || return 1
        generate_nginx_config_for_machine "$machine" || return 1
        generate_deployment_script_for_machine "$machine" || return 1
    done <<< "$machines"

    # Generate master deployment script
    generate_master_deployment_script || return 1

    log_success "Translation completed! Generated files in: $OUTPUT_DIR"
    return 0
}

# Function: generate_master_deployment_script
# Description: Generates a master script to deploy to all machines
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_master_deployment_script() {
    local master_script="$OUTPUT_DIR/deploy-all.sh"

    log_info "Generating master deployment script..."

    cat > "$master_script" <<EOF
#!/bin/bash
# Master deployment script for all machines
# Generated: $(date)

set -e

SCRIPT_DIR="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"

echo "🚀 Starting deployment to all machines..."

# Deploy to each machine
EOF

    # Add deployment commands for each machine
    local machines
    machines=$(get_machine_list)

    while IFS= read -r machine; do
        [[ -z "$machine" ]] && continue

        cat >> "$master_script" <<EOF

echo "📦 Deploying to $machine..."
if "\$SCRIPT_DIR/$machine/deploy.sh"; then
    echo "✅ $machine deployment successful"
else
    echo "❌ $machine deployment failed"
    exit 1
fi
EOF
    done <<< "$machines"

    cat >> "$master_script" <<EOF

echo "🎉 All deployments completed successfully!"
EOF

    chmod +x "$master_script"

    log_success "Generated master deployment script at: $master_script"
    return 0
}

# Function: usage
# Description: Shows usage information
# Arguments: None
# Returns: None
usage() {
    cat <<EOF
Docker Compose Translation Engine

USAGE:
    $0 [OPTIONS]

OPTIONS:
    -c, --config FILE    Path to homelab.yaml (default: ./homelab.yaml)
    -o, --output DIR     Output directory (default: ./generated/docker-compose)
    -h, --help          Show this help message

EXAMPLES:
    $0                                    # Use default paths
    $0 -c /path/to/homelab.yaml          # Custom config path
    $0 -o /path/to/output                # Custom output directory

DESCRIPTION:
    Translates homelab.yaml configuration to Docker Compose files for
    distributed deployment across multiple machines. Generates:

    - Per-machine docker-compose.yaml files
    - Nginx reverse proxy configurations
    - Deployment scripts for each machine
    - Master deployment script for all machines

EOF
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -c|--config)
                HOMELAB_CONFIG="$2"
                shift 2
                ;;
            -o|--output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            generate-nginx-bundles)
                # Special command to only generate nginx bundles
                generate_nginx_bundles "$HOMELAB_CONFIG"
                exit $?
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Run translation
    translate_homelab_to_compose
}

# Function: is_web_service
# Description: Determines if a service should be exposed via nginx proxy
# Arguments: $1 - service name, $2 - config file path
# Returns: 0 if service should be exposed, 1 if not
is_web_service() {
    local service="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    # Check if service has a custom domain configured
    local custom_domain
    custom_domain=$(yq ".services[\"$service\"].domain" "$config_file" 2>/dev/null | tr -d '"')

    if [[ -n "$custom_domain" && "$custom_domain" != "null" ]]; then
        return 0  # Has explicit domain configuration
    fi

    # Check if service has a port (indicating it's a service that could be exposed)
    # and doesn't explicitly disable web exposure
    local port
    port=$(yq ".services[\"$service\"].port" "$config_file" 2>/dev/null | tr -d '"')

    local web_enabled
    web_enabled=$(yq ".services[\"$service\"].web" "$config_file" 2>/dev/null | tr -d '"')

    # Default web to true if not specified
    if [[ -z "$web_enabled" || "$web_enabled" == "null" ]]; then
        web_enabled="true"
    fi

    # Service is a web service if:
    # 1. It has a port AND
    # 2. web is not explicitly set to false
    if [[ -n "$port" && "$port" != "null" && "$web_enabled" != "false" ]]; then
        return 0  # Service should be exposed
    fi

    return 1  # Service should not be exposed via nginx
}

# Function: get_base_domain
# Description: Gets the base domain from environment or config
# Arguments: $1 - config file path
# Returns: Base domain string
get_base_domain() {
    local config_file="${1:-$HOMELAB_CONFIG}"

    # Try environment first, then config, then default
    local base_domain="${BASE_DOMAIN:-}"

    if [[ -z "$base_domain" ]]; then
        base_domain=$(yq ".environment.BASE_DOMAIN // \"homelab.local\"" "$config_file" 2>/dev/null | tr -d '"')
    fi

    echo "$base_domain"
}

# Function: generate_nginx_bundles
# Description: Generates nginx bundles for all machines
# Arguments: $1 - config file path
# Returns: 0 on success, 1 on failure
generate_nginx_bundles() {
    local config_file="${1:-$HOMELAB_CONFIG}"

    log_info "Generating nginx bundles for all machines..."

    # Get all machines
    local machines
    machines=$(get_machine_list "$config_file") || return 1

    # Generate nginx config for each machine
    while IFS= read -r machine; do
        [[ -z "$machine" ]] && continue

        log_info "Generating nginx bundle for: $machine"
        generate_nginx_config_for_machine "$machine" "$config_file" || return 1
    done <<< "$machines"

    log_success "Generated nginx bundles for all machines"
    return 0
}

# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
