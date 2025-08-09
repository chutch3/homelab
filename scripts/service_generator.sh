#!/bin/bash

# Service Generator
# Generates deployment files (docker-compose, nginx templates, domains) from unified services.yaml

# Set default paths
PROJECT_ROOT="${PROJECT_ROOT:-$PWD}"
SERVICES_CONFIG="${SERVICES_CONFIG:-$PROJECT_ROOT/config/services.yaml}"
GENERATED_COMPOSE="${GENERATED_COMPOSE:-$PROJECT_ROOT/generated-docker-compose.yaml}"
GENERATED_NGINX_DIR="${GENERATED_NGINX_DIR:-$PROJECT_ROOT/generated-nginx}"
DOMAINS_FILE="${DOMAINS_FILE:-$PROJECT_ROOT/.domains}"

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
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        echo "  Processing service: $service_key"

        # Add service name and configuration
        {
            echo "  ${service_key}:"
            # Get service compose configuration and properly indent (convert from JSON to YAML)
            yq --yaml-output ".services[\"${service_key}\"].compose" "$SERVICES_CONFIG" | sed 's/^/    /'
            echo ""
        } >> "$GENERATED_COMPOSE"
    done

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
# Description: Generates nginx template files from services.yaml
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
    yq '.services | keys[]' "$SERVICES_CONFIG" | while read -r service_key; do
        service_key=$(echo "$service_key" | tr -d '"')
        echo "  Processing nginx config for: $service_key"

        # Get domain and nginx configuration with proper escaping
        domain=$(yq ".services[\"${service_key}\"].domain" "$SERVICES_CONFIG" | tr -d '"')
        additional_config=$(yq -r ".services[\"${service_key}\"].nginx.additional_config" "$SERVICES_CONFIG")

        # Generate normalized domain variable name
        domain_var=$(normalize_service_name_for_env "$service_key")

        # Generate nginx template
        cat > "$GENERATED_NGINX_DIR/${service_key}.template" <<EOF
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name \${DOMAIN_${domain_var}};

    include /etc/nginx/conf.d/includes/ssl;

$(echo "$additional_config" | sed 's/^/    /' | sed 's/null//')

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

# Function: generate_all_from_services
# Description: Generates all deployment files from services.yaml
# Arguments: None
# Returns: 0 on success, 1 on failure
generate_all_from_services() {
    echo "🚀 Generating all deployment files from services configuration..."

    generate_compose_from_services || return 1
    generate_nginx_from_services || return 1
    generate_domains_from_services || return 1

    echo "✅ All deployment files generated successfully!"
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

# Note: Functions are available when script is sourced
