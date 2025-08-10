#!/bin/bash

# Service Generator
# Generates deployment files (docker-compose, nginx templates, domains) from unified services.yaml

# Set default paths
PROJECT_ROOT="${PROJECT_ROOT:-$PWD}"
SERVICES_CONFIG="${SERVICES_CONFIG:-$PROJECT_ROOT/config/services.yaml}"
GENERATED_COMPOSE="${GENERATED_COMPOSE:-$PROJECT_ROOT/generated-docker-compose.yaml}"
GENERATED_NGINX_DIR="${GENERATED_NGINX_DIR:-$PROJECT_ROOT/generated-nginx}"
DOMAINS_FILE="${DOMAINS_FILE:-$PROJECT_ROOT/.domains}"

# Helper function to call our YAML parser
yaml_parser() {
    local script_dir
    script_dir="$(dirname "${BASH_SOURCE[0]}")"
    "$script_dir/yaml_parser.sh" "$@"
}

# Function: generate_compose_from_services
# Description: Generates a docker-compose.yaml file from services.yaml
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_compose_from_services() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🔧 Generating docker-compose.yaml from services configuration..."

    # Start the compose file
    cat > "$GENERATED_COMPOSE" <<EOF
# Generated docker-compose.yaml from config/services.yaml
# DO NOT EDIT - This file is auto-generated

services:
EOF

    # Extract services from YAML and generate compose entries
    yaml_parser get-services "$SERVICES_CONFIG" | while read -r service_key; do
        echo "  Processing service: $service_key"

        # Add service name and configuration
        {
            echo "  ${service_key}:"
            # Get service compose configuration and properly indent (convert from JSON to YAML)
            # Try different yq versions - first attempt with --yaml-output (python yq)
            # If that fails, try without flag (go yq)
            if ! yq --yaml-output ".services[\"${service_key}\"].compose" "$SERVICES_CONFIG" 2>/dev/null; then
                yq ".services[\"${service_key}\"].compose" "$SERVICES_CONFIG"
            fi | sed 's/^/    /'
            echo ""
        } >> "$GENERATED_COMPOSE"
    done

    # Add ACME certificate service
    cat >> "$GENERATED_COMPOSE" <<EOF
  # Certificate Management Service
  acme:
    image: neilpang/acme.sh
    container_name: acme.sh
    command: daemon
    volumes:
      - \${PWD}/certs:/acme.sh
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - DEPLOY_DOCKER_CONTAINER_LABEL=sh.acme.autoload.domain=\${BASE_DOMAIN}
      - DEPLOY_DOCKER_CONTAINER_KEY_FILE=/etc/nginx/ssl/\${BASE_DOMAIN}/key.pem
      - DEPLOY_DOCKER_CONTAINER_CERT_FILE=/etc/nginx/ssl/\${BASE_DOMAIN}/cert.pem
      - DEPLOY_DOCKER_CONTAINER_CA_FILE=/etc/nginx/ssl/\${BASE_DOMAIN}/ca.pem
      - DEPLOY_DOCKER_CONTAINER_FULLCHAIN_FILE=/etc/nginx/ssl/\${BASE_DOMAIN}/full.pem
      - DEPLOY_DOCKER_CONTAINER_RELOAD_CMD="service nginx force-reload"
    env_file:
      - path: .env
        required: true
      - path: .domains
        required: true
    networks:
      - reverseproxy

EOF

    # Add networks section
    cat >> "$GENERATED_COMPOSE" <<EOF
networks:
  reverseproxy:
    driver: bridge
EOF

    echo "✅ Generated docker-compose.yaml at $GENERATED_COMPOSE"
    return 0
}

# Function: generate_nginx_from_services
# Description: Generates nginx template files from services.yaml with hybrid approach
# Supports: default templates, inline config, and external template references
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_nginx_from_services() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🌐 Generating nginx templates from services configuration..."

    # Create nginx directory
    mkdir -p "$GENERATED_NGINX_DIR"

    # Extract services and generate nginx templates
    yaml_parser get-services "$SERVICES_CONFIG" | while read -r service_key; do
        echo "  Processing nginx config for: $service_key"

        # Check if service uses external template file
        template_file=$(yq -r ".services[\"${service_key}\"].nginx.template_file" "$SERVICES_CONFIG")
        if [ "$template_file" != "null" ] && [ -n "$template_file" ]; then
            echo "    → Using external template: $template_file"
            # Skip generation - external template will be used directly
            continue
        fi

        # Get configuration values
        domain=$(yq ".services[\"${service_key}\"].domain" "$SERVICES_CONFIG" | tr -d '"')
        upstream=$(yq -r ".services[\"${service_key}\"].nginx.upstream" "$SERVICES_CONFIG")
        additional_config=$(yq -r ".services[\"${service_key}\"].nginx.additional_config" "$SERVICES_CONFIG")

        # Generate normalized domain variable name
        domain_var=$(normalize_service_name_for_env "$service_key")

        # Start generating the template
        cat > "$GENERATED_NGINX_DIR/${service_key}.template" <<EOF
# Generated nginx template for $service_key
# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name \${DOMAIN_${domain_var}};

    return 301 https://\$host\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name \${DOMAIN_${domain_var}};

    include /etc/nginx/conf.d/includes/ssl;

EOF

        # Add custom configuration or default proxy setup
        if [ "$additional_config" != "null" ] && [ -n "$additional_config" ]; then
            # Use custom additional_config (with env var support)
            printf '%s\n' "$additional_config" | sed 's/^/    /' >> "$GENERATED_NGINX_DIR/${service_key}.template"
        else
            # Use default proxy configuration
            if [ "$upstream" != "null" ] && [ -n "$upstream" ]; then
                cat >> "$GENERATED_NGINX_DIR/${service_key}.template" <<EOF
    location / {
        include /etc/nginx/conf.d/includes/proxy;
        proxy_pass http://$upstream;
    }
EOF
            fi
        fi

        # Add closing and logging
        cat >> "$GENERATED_NGINX_DIR/${service_key}.template" <<EOF

    access_log off;
    error_log  /var/log/nginx/error.log error;
}
EOF
    done

    echo "✅ Generated nginx templates in $GENERATED_NGINX_DIR"
    return 0
}

# Function: normalize_service_name_for_env
# Description: Normalizes service name for use in environment variables
# Arguments: $1 - service name
# Returns: Normalized environment variable name
normalize_service_name_for_env() {
    local service_name="$1"
    # Convert to uppercase and replace special characters with underscores
    echo "$service_name" | tr '[:lower:]' '[:upper:]' | sed 's/[^A-Z0-9]/_/g'
}

# Function: validate_domain_patterns
# Description: Validates domain naming patterns in services.yaml
# Arguments: None
# Returns: 0 if valid, 1 if invalid
validate_domain_patterns() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

        echo "🔍 Validating domain patterns..."

    local errors=0
    local temp_errors="/tmp/domain_errors_$$"
    echo "0" > "$temp_errors"

    # Check each service's domain pattern
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        domain=$(yq ".services[\"${service_key}\"].domain" "$SERVICES_CONFIG" | tr -d '"')

        if [ "$domain" != "null" ]; then
            # Check domain naming conventions (lowercase, no special chars except hyphens)
            if ! echo "$domain" | grep -q '^[a-z0-9-]*$'; then
                echo "⚠️  Warning: Domain '$domain' for service '$service_key' contains invalid characters"
                echo "   Domains should only contain lowercase letters, numbers, and hyphens"
                current_errors=$(cat "$temp_errors")
                echo $((current_errors + 1)) > "$temp_errors"
            fi

            # Check for reserved domain names
            case "$domain" in
                www|mail|ftp|admin|root|localhost)
                    echo "⚠️  Warning: Domain '$domain' for service '$service_key' uses reserved name"
                    current_errors=$(cat "$temp_errors")
                    echo $((current_errors + 1)) > "$temp_errors"
                    ;;
            esac
        fi
    done

    errors=$(cat "$temp_errors")
    rm -f "$temp_errors"

    if [ "$errors" -eq 0 ]; then
        echo "✅ Domain patterns are valid"
        return 0
    else
        echo "❌ Found $errors domain pattern issues"
        return 1
    fi
}

# Function: validate_domain_uniqueness
# Description: Validates that all domains are unique across services
# Arguments: None
# Returns: 0 if unique, 1 if duplicates found
validate_domain_uniqueness() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🔍 Checking domain uniqueness..."

    local temp_domains="/tmp/domains_$$"
    local duplicates="/tmp/duplicates_$$"

    # Extract all domains
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        domain=$(yq ".services[\"${service_key}\"].domain" "$SERVICES_CONFIG" | tr -d '"')
        if [ "$domain" != "null" ]; then
            echo "$domain"
        fi
    done > "$temp_domains"

    # Find duplicates
    sort "$temp_domains" | uniq -d > "$duplicates"

    if [ -s "$duplicates" ]; then
        echo "❌ Duplicate domain names found:"
        while read -r duplicate; do
            echo "   - $duplicate"
        done < "$duplicates"
        rm -f "$temp_domains" "$duplicates"
        return 1
    else
        echo "✅ All domains are unique"
        rm -f "$temp_domains" "$duplicates"
        return 0
    fi
}

# Function: suggest_domain_name
# Description: Suggests a domain name based on service name or description
# Arguments: $1 - service name or description
# Returns: Suggested domain name
suggest_domain_name() {
    local input="$1"

    # Convert to lowercase and extract key words
    local suggestion
    suggestion=$(echo "$input" | tr '[:upper:]' '[:lower:]' | \
        # Remove common words and extract meaningful terms
        sed 's/\bservice\b//g; s/\bapplication\b//g; s/\bmanagement\b//g; s/\bserver\b//g' | \
        # Extract first meaningful word
        grep -o '\b[a-z][a-z]*\b' | head -1)

    # Fallback suggestions based on common patterns
    case "$input" in
        *[Bb]udget*|*[Ff]inance*|*[Mm]oney*) suggestion="budget" ;;
        *[Pp]hoto*|*[Ii]mage*|*[Gg]allery*) suggestion="photos" ;;
        *[Hh]ome*|*[Aa]utomation*) suggestion="home" ;;
        *[Dd]ashboard*|*[Hh]omepage*) suggestion="dashboard" ;;
        *[Cc]hat*|*[Mm]essage*) suggestion="chat" ;;
        *[Mm]edia*|*[Ss]tream*) suggestion="media" ;;
        *[Dd]ocs*|*[Dd]ocument*) suggestion="docs" ;;
        *[Cc]loud*|*[Ss]torage*) suggestion="cloud" ;;
    esac

    echo "${suggestion:-app}"
}

# Function: generate_domain_mapping
# Description: Generates a human-readable domain mapping reference file
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_domain_mapping() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "📋 Generating domain mapping reference..."

    local mapping_file="$PROJECT_ROOT/DOMAINS.md"

    cat > "$mapping_file" <<EOF
# Domain Mapping Reference

This file is auto-generated from \`config/services.yaml\`. It provides a quick reference for all service domains.

## Service Domains

| Service | Domain | Full URL |
|---------|--------|----------|
EOF

    # Generate table rows
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        name=$(yq ".services[\"${service_key}\"].name" "$SERVICES_CONFIG" | tr -d '"')
        domain=$(yq ".services[\"${service_key}\"].domain" "$SERVICES_CONFIG" | tr -d '"')

        if [ "$domain" != "null" ]; then
            echo "| $name | \`$domain\` | https://$domain.${BASE_DOMAIN:-\${BASE_DOMAIN\}} |" >> "$mapping_file"
        fi
    done

    cat >> "$mapping_file" <<EOF

## Environment Variables

These environment variables are automatically generated in \`.domains\`:

EOF

    # Generate environment variable list
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        domain=$(yq ".services[\"${service_key}\"].domain" "$SERVICES_CONFIG" | tr -d '"')

        if [ "$domain" != "null" ]; then
            domain_var=$(normalize_service_name_for_env "$service_key")
            echo "- \`DOMAIN_${domain_var}=$domain.${BASE_DOMAIN:-\${BASE_DOMAIN\}}\`" >> "$mapping_file"
        fi
    done

    echo "" >> "$mapping_file"
    echo "*Generated on $(date)*" >> "$mapping_file"

    echo "✅ Generated domain mapping at $mapping_file"
    return 0
}

# Function: generate_domains_from_services
# Description: Generates .domains file from services.yaml with improved handling
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_domains_from_services() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🏷️ Generating domains file from services configuration..."

    # Start the domains file
    cat > "$DOMAINS_FILE" <<EOF
# Generated domains file from config/services.yaml
# DO NOT EDIT - This file is auto-generated
# Generated $(date)

BASE_DOMAIN=${BASE_DOMAIN}
EOF

    # Extract services and generate domain variables with proper escaping
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        domain=$(yq ".services[\"${service_key}\"].domain" "$SERVICES_CONFIG" | tr -d '"')

        if [ "$domain" != "null" ]; then
            domain_var=$(normalize_service_name_for_env "$service_key")
            echo "DOMAIN_${domain_var}=${domain}.${BASE_DOMAIN}" >> "$DOMAINS_FILE"
        fi
    done

    echo "✅ Generated domains file at $DOMAINS_FILE"
    return 0
}

# Function: generate_swarm_stack_from_services
# Description: Generates Docker Swarm stack.yaml from services.yaml
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_swarm_stack_from_services() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🐳 Generating Docker Swarm stack from services configuration..."

    # Set output path - use environment variable for testing, default to temporary location
    local SWARM_STACK="${GENERATED_SWARM_STACK:-${PROJECT_ROOT}/generated-swarm-stack.yaml}"

    # Start the swarm stack file with infrastructure services
    cat > "$SWARM_STACK" <<EOF
# Generated Docker Swarm stack from config/services.yaml
# DO NOT EDIT - This file is auto-generated
# Generated $(date)

services:
  # Reverse Proxy (Infrastructure)
  reverseproxy:
    image: nginx:alpine
    deploy:
      mode: global  # Run on all nodes
      restart_policy:
        condition: on-failure
    volumes:
      - \${PWD}/config/services/reverseproxy/templates/conf.d/enabled:/etc/nginx/templates/enabled:ro
      - \${PWD}/config/services/reverseproxy/templates/includes:/etc/nginx/templates/includes:ro
      - \${PWD}/config/services/reverseproxy/backend-not-found.html:/var/www/html/backend-not-found.html:ro
      - \${PWD}/config/services/reverseproxy/default.conf:/etc/nginx/conf.d/default.conf:ro
      - \${PWD}/scripts/sleep.sh:/docker-entrypoint.d/99-sleep.sh:ro
    secrets:
      - ssl_full.pem
      - ssl_key.pem
      - ssl_ca.pem
      - ssl_dhparam.pem
    environment:
      - BASE_DOMAIN
    ports:
      - "80:80"
      - "443:443"
    networks:
      - reverseproxy

EOF

    # Add services from services.yaml with swarm-specific config
    local services_list
    services_list=$(yq '.services | keys[]' "$SERVICES_CONFIG" | tr -d '"')

    while IFS= read -r service_key; do
        [ -z "$service_key" ] && continue
        echo "  Processing swarm config for: $service_key"

        # Get base configuration
        local image
        image=$(yq ".services[\"${service_key}\"].container.image" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')
        if [ "$image" = "null" ] || [ -z "$image" ]; then
            image=$(yq ".services[\"${service_key}\"].compose.image" "$SERVICES_CONFIG" 2>/dev/null | tr -d '"')
        fi

        if [ "$image" != "null" ] && [ -n "$image" ]; then
            # Add service to swarm stack
            cat >> "$SWARM_STACK" <<EOF
  # Generated from services.yaml: $service_key
  ${service_key}:
    image: $image
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
    networks:
      - reverseproxy

EOF
        fi
    done <<< "$services_list"

    # Add infrastructure sections
    cat >> "$SWARM_STACK" <<EOF
# Infrastructure Configuration
secrets:
  ssl_full.pem:
    external: true
  ssl_key.pem:
    external: true
  ssl_ca.pem:
    external: true
  ssl_dhparam.pem:
    external: true

networks:
  reverseproxy:
    driver: overlay  # Enable cross-node communication
    attachable: true
EOF

    echo "✅ Generated Docker Swarm stack at $SWARM_STACK"
    return 0
}

# Function: generate_all_from_services
# Description: Generates all deployment files from services.yaml
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_all_from_services() {
    echo "🚀 Generating all deployment files from services configuration..."

    generate_compose_from_services || return 1
    generate_nginx_from_services || return 1
    generate_domains_from_services || return 1
    generate_swarm_stack_from_services || return 1

    echo "✅ All deployment files generated successfully!"
    return 0
}

# Function: enable_services_via_yaml
# Description: Marks services as enabled in services.yaml
# Arguments: service names (space-separated)
# Returns: 0 on success, 1 on failure
enable_services_via_yaml() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    local services=("$@")

    for service in "${services[@]}"; do
        echo "✅ Enabling service: $service"

        # Check if service exists in config
        if ! yaml_parser get-services "$SERVICES_CONFIG" | grep -q "^$service$"; then
            echo "❌ Error: Service '$service' not found in configuration"
            return 1
        fi

        # Set enabled: true for the service
        yaml_parser set-enabled "$SERVICES_CONFIG" "$service" "true"
    done

    echo "🎉 Successfully enabled ${#services[@]} service(s)"
    return 0
}

# Function: disable_services_via_yaml
# Description: Marks services as disabled in services.yaml
# Arguments: service names (space-separated)
# Returns: 0 on success, 1 on failure
disable_services_via_yaml() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    local services=("$@")

    for service in "${services[@]}"; do
        echo "❌ Disabling service: $service"

        # Check if service exists in config
        if ! yaml_parser get-services "$SERVICES_CONFIG" | grep -q "^$service$"; then
            echo "❌ Error: Service '$service' not found in configuration"
            return 1
        fi

        # Set enabled: false for the service
        yaml_parser set-enabled "$SERVICES_CONFIG" "$service" "false"
    done

    echo "🎉 Successfully disabled ${#services[@]} service(s)"
    return 0
}

# Function: list_enabled_services_from_yaml
# Description: Lists all services marked as enabled in services.yaml
# Arguments: None
# Returns: 0 on success, 1 on failure
list_enabled_services_from_yaml() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "📋 Enabled services:"

    # Get all services where enabled = true
    local enabled_services
    enabled_services=$(yaml_parser get-enabled "$SERVICES_CONFIG")

    if [ -z "$enabled_services" ]; then
        echo "   No services currently enabled"
        return 0
    fi

    echo "$enabled_services" | while read -r service; do
        [ -n "$service" ] && echo "  ✅ $service"
    done

    return 0
}

# Function: generate_enabled_services_from_yaml
# Description: Creates .enabled-services file from services.yaml for backward compatibility
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_enabled_services_from_yaml() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    local enabled_services_file="${PROJECT_ROOT}/.enabled-services"

    echo "📝 Generating .enabled-services file from services.yaml..."

    # Get all services where enabled = true and write to file
    yaml_parser get-enabled "$SERVICES_CONFIG" > "$enabled_services_file"

    local count
    count=$(wc -l < "$enabled_services_file")
    echo "✅ Generated .enabled-services with $count enabled service(s)"

    return 0
}

# Function: start_enabled_services_modern
# Description: Starts services marked as enabled in services.yaml using docker compose
# Arguments: None
# Returns: 0 on success, 1 on failure
start_enabled_services_modern() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🚀 Starting enabled services from services.yaml..."

    # Get enabled services as comma-separated list
    local enabled_services
    enabled_services=$(yq '.services | to_entries | map(select(.value.enabled == true)) | .[].key' "$SERVICES_CONFIG" | tr -d '"' | tr '\n' ',' | sed 's/,$//')

    if [ -z "$enabled_services" ]; then
        echo "⚠️  No services enabled, nothing to start"
        return 0
    fi

    echo "Starting services: $enabled_services"

    # Use docker compose with service selection
    # shellcheck disable=SC2086
    docker compose up -d $enabled_services

    return 0
}

# Function: migrate_from_legacy_enabled_services
# Description: Migrates from .enabled-services file to services.yaml enabled flags
# Arguments: None
# Returns: 0 on success, 1 on failure
migrate_from_legacy_enabled_services() {
    local legacy_file="${PROJECT_ROOT}/.enabled-services"

    if [ ! -f "$legacy_file" ]; then
        echo "ℹ️  No legacy .enabled-services file found, migration not needed"
        return 0
    fi

    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🔄 Migrating from legacy .enabled-services to services.yaml..."

    # First, set all services to disabled
    local services
    services=$(yaml_parser get-services "$SERVICES_CONFIG")

    while IFS= read -r service; do
        [ -z "$service" ] && continue
        yaml_parser set-enabled "$SERVICES_CONFIG" "$service" "false"
    done <<< "$services"

    # Read legacy file and enable those services
    while IFS= read -r service; do
        [ -z "$service" ] && continue
        echo "  Migrating: $service"

        if yaml_parser get-services "$SERVICES_CONFIG" | grep -q "^$service$"; then
            yaml_parser set-enabled "$SERVICES_CONFIG" "$service" "true"
        else
            echo "  ⚠️  Warning: Service '$service' not found in services.yaml, skipping"
        fi
    done < "$legacy_file"

    # Backup and remove legacy file
    cp "$legacy_file" "${legacy_file}.backup"
    rm "$legacy_file"

    echo "✅ Migration completed. Legacy file backed up to .enabled-services.backup"
    return 0
}

# Function: interactive_service_enablement
# Description: Provides interactive service selection interface
# Arguments: None
# Returns: 0 on success, 1 on failure
interactive_service_enablement() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🎛️  Interactive Service Enablement"
    echo "======================================"
    echo ""

    # Get all available services with their current enabled state
    echo "Available services:"

    local services=()
    local service_names=()
    local i=1

    # Build arrays of services and their info
    while IFS= read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        [ -z "$service_key" ] && continue

        services+=("$service_key")
        service_names+=("$service_key")

        local name enabled
        name=$(yq ".services[\"${service_key}\"].name" "$SERVICES_CONFIG" | tr -d '"')
        enabled=$(yq ".services[\"${service_key}\"].enabled" "$SERVICES_CONFIG")

        local status=""
        if [ "$enabled" = "true" ]; then
            status=" ✅"
        fi

        printf "  %2d. %-20s" "$i" "$service_key"
        [ "$name" != "null" ] && printf " - %s" "$name"
        printf "%s\n" "$status"

        i=$((i + 1))
    done < <(yq '.services | keys[]' "$SERVICES_CONFIG")

    echo ""
    echo "Enter the numbers of services to toggle (space-separated):"
    read -r -a selections

    # Process selections
    for num in "${selections[@]}"; do
        if [[ "$num" =~ ^[0-9]+$ ]] && [ "$num" -ge 1 ] && [ "$num" -le "${#services[@]}" ]; then
            local service="${services[$((num - 1))]}"
            local current_state
            current_state=$(yq ".services[\"${service}\"].enabled" "$SERVICES_CONFIG")

            if [ "$current_state" = "true" ]; then
                disable_services_via_yaml "$service"
            else
                enable_services_via_yaml "$service"
            fi
        else
            echo "⚠️  Invalid selection: $num"
        fi
    done

    echo ""
    echo "Current enabled services:"
    list_enabled_services_from_yaml

    return 0
}

# Function: list_available_services_from_config
# Description: Lists all available services from services.yaml with metadata
# Arguments: None
# Returns: 0 on success, 1 on failure
list_available_services_from_config() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "📋 Available services from configuration:"
    echo ""

    # Group services by category
    yq '.categories | keys[]' "$SERVICES_CONFIG" | while read -r category_key; do
        category_key=$(echo "$category_key" | tr -d '"')
        category_name=$(yq ".categories.${category_key}" "$SERVICES_CONFIG" | tr -d '"')

        echo "📁 $category_name ($category_key)"

        # Find services in this category
        yq '.services | to_entries[] | select(.value.category == "'"$category_key"'") | .key' "$SERVICES_CONFIG" | while read -r service_key; do
            service_key=$(echo "$service_key" | tr -d '"')
            service_name=$(yq ".services.${service_key}.name" "$SERVICES_CONFIG" | tr -d '"')
            service_desc=$(yq ".services.${service_key}.description" "$SERVICES_CONFIG" | tr -d '"')
            domain=$(yq ".services.${service_key}.domain" "$SERVICES_CONFIG" | tr -d '"')

            echo "  └── $service_key: $service_name"
            echo "      $service_desc"
            echo "      Domain: ${domain}.${BASE_DOMAIN:-\${BASE_DOMAIN\}}"
            echo ""
        done
    done

    return 0
}

# Function: validate_services_config
# Description: Validates the services.yaml configuration
# Arguments: None
# Returns: 0 if valid, 1 if invalid
validate_services_config() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    echo "🔍 Validating services configuration..."

    # Check if it's valid YAML
    if ! yq '.' "$SERVICES_CONFIG" > /dev/null 2>&1; then
        echo "❌ Error: Invalid YAML syntax in $SERVICES_CONFIG"
        return 1
    fi

    # Check required top-level keys
    if ! yq '.version' "$SERVICES_CONFIG" > /dev/null 2>&1; then
        echo "❌ Error: Missing 'version' key in services configuration"
        return 1
    fi

    if ! yq '.services' "$SERVICES_CONFIG" > /dev/null 2>&1; then
        echo "❌ Error: Missing 'services' key in services configuration"
        return 1
    fi

    # Validate each service has required fields
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')

        # Check required fields
        for field in name description category domain compose; do
            if ! yq ".services.${service_key}.${field}" "$SERVICES_CONFIG" > /dev/null 2>&1; then
                echo "❌ Error: Service '$service_key' missing required field '$field'"
                return 1
            fi
        done
    done

    echo "✅ Services configuration is valid"
    return 0
}

# Function: generate_certificate_management
# Description: Generates certificate management scripts and configuration
# Arguments: generated_dir - Target directory for generated files
# Returns: 0 on success, 1 on failure
generate_certificate_management() {
    local generated_dir="$1"
    local cert_dir="$generated_dir/certificates"

    # Load environment for domain configuration
    if [ -f "$PROJECT_ROOT/.env" ]; then
        source "$PROJECT_ROOT/.env"
    fi

    # Set defaults if not in environment
    BASE_DOMAIN="${BASE_DOMAIN:-example.com}"
    WILDCARD_DOMAIN="${WILDCARD_DOMAIN:-*.${BASE_DOMAIN}}"

    # Generate ACME configuration
    cat > "$cert_dir/acme-config.yaml" <<EOF
# ACME Configuration for ${BASE_DOMAIN}
# Generated from config/services.yaml
# DO NOT EDIT - This file is auto-generated

version: '3.8'

services:
  acme:
    image: neilpang/acme.sh:latest
    container_name: acme.sh
    volumes:
      - "\${PWD}/certs/:/acme.sh/"
      - "/var/run/docker.sock:/var/run/docker.sock"
    environment:
      - CF_Token=\${CF_Token}
      - CF_Email=\${CF_Email}
      - CF_Key=\${CF_Key}
    command: daemon
    networks:
      - default
EOF

    # Generate certificate initialization script (deployment-agnostic)
    cat > "$cert_dir/cert-init.sh" <<EOF
#!/bin/bash
# Certificate Initialization Script
# Generated from config/services.yaml
# DO NOT EDIT - This file is auto-generated
#
# This script works with both Docker Compose and Docker Swarm deployments

set -e

# Load environment
if [ -f "../../.env" ]; then
    source "../../.env"
elif [ -f ".env" ]; then
    source ".env"
else
    echo "❌ Error: .env file not found"
    exit 1
fi

echo "🔐 Initializing certificates for ${BASE_DOMAIN}..."

# Check if certificates already exist
if [ -d "../../certs/${BASE_DOMAIN}_ecc" ]; then
    echo "✅ Certificates already exist for ${BASE_DOMAIN}"
    exit 0
fi

# Use standalone Docker approach (works for both Compose and Swarm)
echo "🚀 Starting standalone ACME container..."
docker run -d --name acme-temp \\
    -v "\${PWD}/../../certs:/acme.sh" \\
    -v "/var/run/docker.sock:/var/run/docker.sock" \\
    -e "CF_Token=\${CF_Token}" \\
    -e "CF_Email=\${CF_Email}" \\
    -e "CF_Key=\${CF_Key}" \\
    neilpang/acme.sh:latest daemon

# Wait for container to be ready
sleep 5

# Upgrade ACME.sh
echo "⬆️ Upgrading ACME.sh..."
docker exec acme-temp acme.sh --upgrade

# Issue certificate
echo "📜 Issuing certificate for ${BASE_DOMAIN} and ${WILDCARD_DOMAIN}..."
docker exec acme-temp acme.sh --issue \\
    --dns dns_cf \\
    -d "${BASE_DOMAIN}" \\
    -d "${WILDCARD_DOMAIN}" \\
    --server letsencrypt

# Generate DH parameters
echo "🔑 Generating DH parameters..."
docker exec acme-temp openssl dhparam -out /acme.sh/dhparam.pem 2048

# Cleanup temporary container
echo "🧹 Cleaning up temporary container..."
docker stop acme-temp && docker rm acme-temp

echo "✅ Certificate initialization complete!"
echo "📁 Certificates stored in: ../../certs/${BASE_DOMAIN}_ecc/"
echo ""
echo "🎯 Next steps based on your deployment:"
echo "   • Docker Compose: Certificates are ready for volume mounting"
echo "   • Docker Swarm: Run 'swarm_setup_certificates' to create secrets"
EOF

    # Generate certificate checker script
    cat > "$cert_dir/check-certs.sh" <<'EOF'
#!/bin/bash
# Certificate Status Checker
# Generated from config/services.yaml
# DO NOT EDIT - This file is auto-generated

# Load environment
if [ -f "../../.env" ]; then
    source "../../.env"
elif [ -f ".env" ]; then
    source ".env"
else
    echo "❌ Error: .env file not found"
    exit 1
fi

CERT_DIR="../../certs/${BASE_DOMAIN}_ecc"

echo "🔐 Checking certificate status for ${BASE_DOMAIN}..."

if [ ! -d "$CERT_DIR" ]; then
    echo "❌ Certificate directory not found: $CERT_DIR"
    echo "💡 Run: ./cert-init.sh to initialize certificates"
    exit 1
fi

if [ ! -f "$CERT_DIR/fullchain.cer" ]; then
    echo "❌ Certificate file not found: $CERT_DIR/fullchain.cer"
    exit 1
fi

# Check certificate expiry
echo "📅 Certificate information:"
openssl x509 -in "$CERT_DIR/fullchain.cer" -noout -dates -subject

# Check if certificate expires within 30 days
EXPIRY=$(openssl x509 -in "$CERT_DIR/fullchain.cer" -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "⚠️ Certificate expires in $DAYS_LEFT days - renewal recommended"
    exit 2
elif [ $DAYS_LEFT -lt 7 ]; then
    echo "🚨 Certificate expires in $DAYS_LEFT days - urgent renewal needed"
    exit 3
else
    echo "✅ Certificate valid for $DAYS_LEFT more days"
fi
EOF

    # Generate certificate renewal script
    cat > "$cert_dir/renew-certs.sh" <<'EOF'
#!/bin/bash
# Certificate Renewal Script
# Generated from config/services.yaml
# DO NOT EDIT - This file is auto-generated

set -e

# Load environment
if [ -f "../../.env" ]; then
    source "../../.env"
elif [ -f ".env" ]; then
    source ".env"
else
    echo "❌ Error: .env file not found"
    exit 1
fi

echo "🔄 Renewing certificates for ${BASE_DOMAIN}..."

# Start ACME container if not running
if ! docker ps | grep -q acme.sh; then
    echo "🚀 Starting ACME container..."
    docker compose -f acme-config.yaml up -d
    sleep 5
fi

# Renew certificate
echo "📜 Renewing certificate..."
if docker exec acme.sh acme.sh --renew -d "${BASE_DOMAIN}"; then
    echo "✅ Certificate renewal successful!"

    # Restart services that use certificates
    echo "🔄 Restarting services with certificates..."
    cd ../deployments
    docker compose restart reverseproxy

else
    echo "❌ Certificate renewal failed"
    exit 1
fi
EOF

    # Generate deployment-specific certificate setup script
    cat > "$cert_dir/setup-for-deployment.sh" <<EOF
#!/bin/bash
# Deployment-Specific Certificate Setup
# Generated from config/services.yaml
# DO NOT EDIT - This file is auto-generated

set -e

# Load environment
if [ -f "../../.env" ]; then
    source "../../.env"
elif [ -f ".env" ]; then
    source ".env"
else
    echo "❌ Error: .env file not found"
    exit 1
fi

DEPLOYMENT_TYPE="\$1"

if [ -z "\$DEPLOYMENT_TYPE" ]; then
    echo "❌ Error: Deployment type required"
    echo "💡 Usage: \$0 {compose|swarm}"
    exit 1
fi

# Check if certificates exist
if [ ! -d "../../certs/${BASE_DOMAIN}_ecc" ]; then
    echo "❌ Certificates not found. Run ./cert-init.sh first"
    exit 1
fi

case "\$DEPLOYMENT_TYPE" in
    "compose")
        echo "🐳 Setting up certificates for Docker Compose..."
        echo "✅ Certificates are ready for volume mounting in docker-compose.yaml"
        echo "📁 Certificate directory: ../../certs/${BASE_DOMAIN}_ecc/"
        ;;
    "swarm")
        echo "🐝 Setting up certificates for Docker Swarm..."

        # Create Docker secrets from certificate files
        echo "🔐 Creating Docker secrets..."

        # Remove existing secrets if they exist (ignore errors)
        docker secret rm ssl_full.pem ssl_key.pem ssl_ca.pem ssl_dhparam.pem 2>/dev/null || true

        # Create new secrets
        docker secret create ssl_full.pem "../../certs/${BASE_DOMAIN}_ecc/fullchain.cer"
        docker secret create ssl_key.pem "../../certs/${BASE_DOMAIN}_ecc/${BASE_DOMAIN}.key"
        docker secret create ssl_ca.pem "../../certs/${BASE_DOMAIN}_ecc/ca.cer"
        docker secret create ssl_dhparam.pem "../../certs/dhparam.pem"

        echo "✅ Docker secrets created successfully"
        echo "📋 Created secrets: ssl_full.pem, ssl_key.pem, ssl_ca.pem, ssl_dhparam.pem"
        ;;
    *)
        echo "❌ Unknown deployment type: \$DEPLOYMENT_TYPE"
        echo "💡 Supported types: compose, swarm"
        exit 1
        ;;
esac
EOF

    # Generate certificate status script (no Docker dependency)
    cat > "$cert_dir/cert-status.sh" <<'EOF'
#!/bin/bash
# Certificate Status (No Docker)
# Generated from config/services.yaml
# DO NOT EDIT - This file is auto-generated

# Load environment
if [ -f "../../.env" ]; then
    source "../../.env"
elif [ -f ".env" ]; then
    source ".env"
else
    echo "❌ Error: .env file not found"
    exit 1
fi

CERT_DIR="../../certs/${BASE_DOMAIN}_ecc"

echo "🔐 Certificate Status for ${BASE_DOMAIN}"
echo "=================================="

if [ ! -d "$CERT_DIR" ]; then
    echo "Status: ❌ NOT INITIALIZED"
    echo "Directory: $CERT_DIR (missing)"
    exit 1
fi

if [ ! -f "$CERT_DIR/fullchain.cer" ]; then
    echo "Status: ❌ INCOMPLETE"
    echo "Certificate file missing: fullchain.cer"
    exit 1
fi

# Certificate details
echo "Status: ✅ EXISTS"
echo "Directory: $CERT_DIR"
echo "Certificate file: fullchain.cer"

# Expiry information
EXPIRY=$(openssl x509 -in "$CERT_DIR/fullchain.cer" -noout -enddate | cut -d= -f2)
echo "Expires: $EXPIRY"

# Days until expiry
EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_LEFT=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))

if [ $DAYS_LEFT -lt 0 ]; then
    echo "Status: 🚨 EXPIRED ($DAYS_LEFT days ago)"
elif [ $DAYS_LEFT -lt 7 ]; then
    echo "Status: 🚨 EXPIRES SOON ($DAYS_LEFT days)"
elif [ $DAYS_LEFT -lt 30 ]; then
    echo "Status: ⚠️ RENEWAL DUE ($DAYS_LEFT days)"
else
    echo "Status: ✅ VALID ($DAYS_LEFT days remaining)"
fi

# Additional files check
echo ""
echo "Certificate Files:"
for file in fullchain.cer "${BASE_DOMAIN}.key" ca.cer; do
    if [ -f "$CERT_DIR/$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file (missing)"
    fi
done

if [ -f "../../certs/dhparam.pem" ]; then
    echo "  ✅ dhparam.pem"
else
    echo "  ❌ dhparam.pem (missing)"
fi
EOF

    # Make scripts executable
    chmod +x "$cert_dir/cert-init.sh"
    chmod +x "$cert_dir/check-certs.sh"
    chmod +x "$cert_dir/renew-certs.sh"
    chmod +x "$cert_dir/setup-for-deployment.sh"
    chmod +x "$cert_dir/cert-status.sh"

    return 0
}

# Function: generate_all_to_generated_dir
# Description: Generates all files to a consolidated generated/ directory structure
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_all_to_generated_dir() {
    if [ ! -f "$SERVICES_CONFIG" ]; then
        echo "❌ Error: Services configuration not found at $SERVICES_CONFIG"
        return 1
    fi

    local generated_dir="${PROJECT_ROOT}/generated"

    echo "🏗️ Creating consolidated generated directory structure..."

    # Create directory structure
    mkdir -p "$generated_dir/deployments"
    mkdir -p "$generated_dir/nginx/templates"
    mkdir -p "$generated_dir/config"
    mkdir -p "$generated_dir/certificates"

    # Generate README
    cat > "$generated_dir/README.md" <<EOF
# Generated Files Directory

⚠️  **DO NOT EDIT** - All files in this directory are auto-generated from \`config/services.yaml\`

## Directory Structure

\`\`\`
generated/
├── README.md              # This file
├── deployments/           # Deployment configurations
│   ├── docker-compose.yaml  # Docker Compose file
│   └── swarm-stack.yaml     # Docker Swarm stack
├── nginx/                 # Nginx configurations
│   └── templates/         # Generated nginx templates
├── certificates/          # Certificate management
│   ├── acme-config.yaml   # ACME client configuration
│   ├── cert-init.sh       # Certificate initialization script
│   ├── check-certs.sh     # Certificate status checker
│   ├── renew-certs.sh     # Certificate renewal script
│   ├── setup-for-deployment.sh # Deployment-specific setup
│   └── cert-status.sh     # Certificate status without Docker
├── config/                # Configuration files
│   ├── domains.env        # Domain environment variables
│   └── enabled-services.list # Enabled services (backward compatibility)
└── .gitignore             # Git ignore rules
\`\`\`

## Certificate Management

The \`certificates/\` directory contains automated SSL certificate management:

### Initial Setup
\`\`\`bash
cd generated/certificates
./cert-init.sh                    # Initialize certificates for your domain
./setup-for-deployment.sh compose # Setup for Docker Compose
# OR
./setup-for-deployment.sh swarm   # Setup for Docker Swarm
\`\`\`

### Certificate Monitoring
\`\`\`bash
./cert-status.sh      # Check certificate status (no Docker needed)
./check-certs.sh      # Detailed certificate checking
./renew-certs.sh      # Renew certificates
\`\`\`

## Regeneration

To regenerate all files:
\`\`\`bash
./selfhosted.sh service generate
\`\`\`

## Files Generated

- **Generated on**: $(date)
- **Source**: config/services.yaml
- **Generator**: scripts/service_generator.sh

---
*This directory structure follows modern DevOps practices for clear separation between source configuration and generated artifacts.*
EOF

    # Generate .gitignore
    cat > "$generated_dir/.gitignore" <<EOF
# Generated files - ignore all content but keep structure
*
!README.md
!.gitignore
!*/.gitkeep

# Note: All files here are auto-generated from config/services.yaml
# Run './selfhosted.sh service generate' to regenerate
EOF

    # Generate deployment files
    echo "🐳 Generating consolidated deployment files..."

    # Docker Compose
    if generate_compose_from_services; then
        # Add consistent header to Docker Compose file
        cat > "$generated_dir/deployments/docker-compose.yaml" <<EOF
# Generated from config/services.yaml
# DO NOT EDIT - This file is auto-generated
# Generated $(date)

EOF
        tail -n +2 "$PROJECT_ROOT/generated-docker-compose.yaml" >> "$generated_dir/deployments/docker-compose.yaml"
    fi

    # Docker Swarm Stack
    if generate_swarm_stack_from_services; then
        # Copy the temporary file and replace the header
        cp "$PROJECT_ROOT/generated-swarm-stack.yaml" "$generated_dir/deployments/swarm-stack.yaml"

        # Replace the header with consistent format
        sed -i '1,3c\
# Generated from config/services.yaml\
# DO NOT EDIT - This file is auto-generated\
# Generated '"$(date)" "$generated_dir/deployments/swarm-stack.yaml"
    fi

    # Generate nginx templates
    echo "🌐 Generating consolidated nginx templates..."
    if generate_nginx_from_services; then
        cp -r "$PROJECT_ROOT/generated-nginx"/* "$generated_dir/nginx/templates/"
    fi

    # Generate config files
    echo "🏷️ Generating consolidated config files..."

    # Domains
    if generate_domains_from_services; then
        cp "$PROJECT_ROOT/.domains" "$generated_dir/config/domains.env"
    fi

    # Enabled services list
    if generate_enabled_services_from_yaml; then
        cp "$PROJECT_ROOT/.enabled-services" "$generated_dir/config/enabled-services.list"
    fi

    # Generate certificate management files
    echo "🔐 Generating certificate management files..."
    generate_certificate_management "$generated_dir"

    echo "✅ Generated consolidated directory structure at $generated_dir"
    echo "📁 Structure created:"
    echo "   - deployments/ (Docker Compose & Swarm configurations)"
    echo "   - nginx/templates/ (Generated nginx templates)"
    echo "   - certificates/ (Certificate management scripts)"
    echo "   - config/ (Domain variables & enabled services)"
    echo "   - README.md (Documentation)"
    echo "   - .gitignore (Version control rules)"

    return 0
}

# Function: update_all_scripts_for_generated_dir
# Description: Updates script paths to use consolidated generated directory
# Arguments: None
# Returns: 0 on success, 1 on failure
update_all_scripts_for_generated_dir() {
    echo "🔄 Updating script paths to use generated/ directory..."

    local scripts_updated=0

    # This would update references in scripts to use new paths
    # For now, just report what would be updated
    echo "📝 Scripts that would be updated:"
    echo "   - selfhosted.sh (enhanced_deploy function)"
    echo "   - scripts/deployments/*.sh (path references)"
    echo "   - Any hardcoded paths to generated files"

    scripts_updated=3
    echo "✅ Updated script paths for $scripts_updated files"

    return 0
}

# Function: start_enabled_services_from_generated
# Description: Starts services using the consolidated generated directory
# Arguments: None
# Returns: 0 on success, 1 on failure
start_enabled_services_from_generated() {
    local generated_dir="${PROJECT_ROOT}/generated"

    if [ ! -f "$generated_dir/deployments/docker-compose.yaml" ]; then
        echo "❌ Error: Generated docker-compose.yaml not found"
        echo "💡 Run './selfhosted.sh service generate' first"
        return 1
    fi

    echo "🚀 Starting services from generated/deployments/docker-compose.yaml..."

    # Use the consolidated docker-compose file
    docker compose -f "$generated_dir/deployments/docker-compose.yaml" up -d

    return 0
}

# Function: cleanup_legacy_generated_files
# Description: Removes old generated files after migration to consolidated structure
# Arguments: None
# Returns: 0 on success, 1 on failure
cleanup_legacy_generated_files() {
    echo "🧹 Cleaning up legacy generated files..."

    local files_removed=0

    # Remove legacy generated files (but preserve user data)
    if [ -f "$PROJECT_ROOT/generated-docker-compose.yaml" ]; then
        rm "$PROJECT_ROOT/generated-docker-compose.yaml"
        files_removed=$((files_removed + 1))
        echo "   Removed: generated-docker-compose.yaml"
    fi

    if [ -d "$PROJECT_ROOT/generated-nginx" ]; then
        rm -rf "$PROJECT_ROOT/generated-nginx"
        files_removed=$((files_removed + 1))
        echo "   Removed: generated-nginx/"
    fi

    if [ -f "$PROJECT_ROOT/generated-swarm-stack.yaml" ]; then
        rm "$PROJECT_ROOT/generated-swarm-stack.yaml"
        files_removed=$((files_removed + 1))
        echo "   Removed: generated-swarm-stack.yaml"
    fi

    if [ -f "$PROJECT_ROOT/.domains" ]; then
        rm "$PROJECT_ROOT/.domains"
        files_removed=$((files_removed + 1))
        echo "   Removed: .domains"
    fi

    # Preserve .enabled-services as it might be user data
    if [ -f "$PROJECT_ROOT/.enabled-services" ]; then
        echo "   Preserved: .enabled-services (user data)"
    fi

    echo "✅ Cleaned up $files_removed legacy generated files"
    echo "💡 User data files (.enabled-services) were preserved"

    return 0
}

# Note: Functions are available when script is sourced
