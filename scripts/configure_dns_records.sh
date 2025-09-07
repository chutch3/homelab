#!/bin/bash
set -euo pipefail

# DNS Records Configuration Script
# Automatically configures Technitium DNS Server with A records for all local services

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/.." && pwd)
STACKS_DIR="$PROJECT_ROOT/stacks"

# Source required scripts
# shellcheck source=scripts/machines.sh
source "$SCRIPT_DIR/machines.sh"

# Colors
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_RED='\033[0;31m'
COLOR_RESET='\033[0m'

log() {
    echo -e "${COLOR_GREEN}[DNS]${COLOR_RESET} $1"
}

log_warn() {
    echo -e "${COLOR_YELLOW}[DNS-WARN]${COLOR_RESET} $1"
}

log_error() {
    echo -e "${COLOR_RED}[DNS-ERROR]${COLOR_RESET} $1" >&2
}

# DNS Server configuration (will be set dynamically based on driver IP)
DNS_SERVER_URL=""
DNS_ADMIN_USER="admin"
get_dns_token() {
    local DNS_ADMIN_PASS="${DNS_ADMIN_PASSWORD:-admin}"
    local response
    local curl_exit_code

    # Use timeout to prevent hanging - URL encode password for special characters
    local encoded_pass
    encoded_pass=$(echo -n "$DNS_ADMIN_PASS" | jq -s -R -r @uri)

    response=$(curl -s --max-time 10 -X POST "${DNS_SERVER_URL}/api/user/login" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "user=${DNS_ADMIN_USER}&pass=${encoded_pass}")
    curl_exit_code=$?

    if [ $curl_exit_code -ne 0 ]; then
        log_error "Failed to connect to DNS server API (exit code: $curl_exit_code)"
        return 1
    fi

    # Check for API error response
    if [[ "$response" == *'"status":"error"'* ]]; then
        local error_msg
        error_msg=$(echo "$response" | sed -n 's/.*"message":\s*"\([^"]*\)".*/\1/p')
        log_error "DNS API error: ${error_msg:-Unknown error}"
        return 1
    fi

    # Extract token from JSON response (more robust parsing)
    local token
    token=$(echo "$response" | sed -n 's/.*"token"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')

    if [ -z "$token" ] || [ "$token" = "null" ]; then
        log_error "Failed to get authentication token from DNS server"
        log_error "Response: $response"
        return 1
    fi

    echo "$token"
}

# Check if DNS record exists via Technitium API
check_record_exists() {
    local name="$1"
    local record_type="${2:-A}"
    local domain="${BASE_DOMAIN:-diyhub.dev}"

    local response
    response=$(curl -s -X POST "${DNS_SERVER_URL}/api/zones/records/get" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "token=${DNS_TOKEN}" \
        -d "domain=${domain}" \
        -d "zone=${domain}")

    # Check if we got a successful response with records
    if [[ "$response" == *'"status":"ok"'* ]]; then
        # Look for the specific record name.domain and type in the response
        local full_name="${name}.${domain}"
        if [[ "$response" == *"\"name\":\"${full_name}\""* ]] && [[ "$response" == *"\"type\":\"${record_type}\""* ]]; then
            return 0  # Record exists
        fi
    fi

    return 1  # Record does not exist
}

# Add DNS A record via Technitium API
add_a_record() {
    local name="$1"
    local ip="$2"
    local domain="${BASE_DOMAIN:-diyhub.dev}"

    # Check if record already exists
    if check_record_exists "$name" "A"; then
        log "A record already exists: ${name}.${domain}"
        return 0
    fi

    local response
    response=$(curl -s -X POST "${DNS_SERVER_URL}/api/zones/records/add" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "token=${DNS_TOKEN}" \
        -d "domain=${name}.${domain}" \
        -d "zone=${domain}" \
        -d "type=A" \
        -d "ipAddress=${ip}" \
        -d "ttl=3600")

    if [[ "$response" == *'"status":"ok"'* ]]; then
        log "✓ Added A record: ${name}.${domain} -> ${ip}"
        return 0
    elif [[ "$response" == *"record already exists"* ]]; then
        log "A record already exists: ${name}.${domain}"
        return 0
    else
        log_warn "Failed to add A record: ${name}.${domain}"
        log_warn "Response: $response"
        return 1
    fi
}

# Add DNS CNAME record via Technitium API
add_cname_record() {
    local name="$1"
    local target="$2"
    local domain="${BASE_DOMAIN:-diyhub.dev}"

    local response
    response=$(curl -s -X POST "${DNS_SERVER_URL}/api/zones/records/add" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "token=${DNS_TOKEN}" \
        -d "domain=${name}.${domain}" \
        -d "zone=${domain}" \
        -d "type=CNAME" \
        -d "overwrite=true" \
        -d "cname=${target}" \
        -d "ttl=3600")

    if [[ "$response" == *'"status":"ok"'* ]]; then
        log "✓ Added CNAME record: ${name}.${domain} -> ${target}"
        return 0
    elif [[ "$response" == *"record already exists"* ]]; then
        log "CNAME record already exists: ${name}.${domain}"
        return 0
    else
        log_warn "Failed to add CNAME record: ${name}.${domain}"
        log_warn "Response: $response"
        return 1
    fi
}

# Function to create DNS zone if it doesn't exist
create_dns_zone() {
    local domain="${BASE_DOMAIN:-diyhub.dev}"

    log "Creating DNS zone: $domain"

    local response
    response=$(curl -s -X POST "$DNS_SERVER_URL/api/zones/create" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "token=${DNS_TOKEN}" \
        -d "zone=$domain" \
        -d "type=Primary")

    if [[ "$response" == *'"status":"ok"'* ]]; then
        log "✓ Created DNS zone: $domain"
    elif [[ "$response" == *"already exists"* ]]; then
        log "DNS zone already exists: $domain"
    else
        log_warn "Failed to create DNS zone: $domain"
        log_warn "Response: $response"
    fi
}

# Function to create _acme-challenge conditional forwarder for Let's Encrypt
create_acme_challenge_forwarder() {
    local domain="${BASE_DOMAIN:-diyhub.dev}"
    local acme_zone="_acme-challenge.${domain}"

    log "Creating _acme-challenge forwarder: $acme_zone"

    local response
    response=$(curl -s -X POST "$DNS_SERVER_URL/api/zones/create" \
        -H "Content-Type: application/x-www-form-urlencoded" \
        -d "token=${DNS_TOKEN}" \
        -d "zone=${acme_zone}" \
        -d "type=Forwarder" \
        -d "forwarder=dan.ns.cloudflare.com")

    if [[ "$response" == *'"status":"ok"'* ]]; then
        log "✓ Created _acme-challenge forwarder for Let's Encrypt DNS validation"
    elif [[ "$response" == *"already exists"* ]]; then
        log "_acme-challenge forwarder already exists: $acme_zone"
    else
        log_warn "Failed to create _acme-challenge forwarder: $acme_zone"
        log_warn "Response: $response"
    fi
}

# Wait for DNS server to be ready
wait_for_dns_server() {
    local retries=30
    local count=0

    log "Waiting for DNS server to be ready..."

    while [ $count -lt $retries ]; do
        if curl -s "$DNS_SERVER_URL/api/user/login" > /dev/null 2>&1; then
            log "DNS server is ready!"
            return 0
        fi

        count=$((count + 1))
        sleep 2
    done

    log_error "DNS server did not become ready in time"
    return 1
}

# Get IP address of machine with specific role
get_manager_ip() {
    local target_role="${1:-manager}"
    local machines_file="${MACHINES_FILE:-$PROJECT_ROOT/machines.yaml}"

    # Get all machine keys from machines.yaml
    local machine_keys
    mapfile -t machine_keys < <(yq '.machines | keys | .[]' "$machines_file" | tr -d '"')

    for machine_key in "${machine_keys[@]}"; do
        local machine_role
        machine_role=$(yq ".machines.\"${machine_key}\".role" "$machines_file" | tr -d '"')

        if [ "$machine_role" = "$target_role" ]; then
            # Found machine with target role, get its IP
            yq ".machines.\"${machine_key}\".ip" "$machines_file" | tr -d '"'
            return 0
        fi
    done

    return 1  # No machine found with target role
}

# Register machine hostnames to their IPs as A records
register_machine_dns_records() {
    log "Registering machine A records..."

    # Get all machine keys from machines.yaml
    local machine_keys
    mapfile -t machine_keys < <(yq '.machines | keys | .[]' "${MACHINES_FILE:-$PROJECT_ROOT/machines.yaml}" | tr -d '"')

    for machine_key in "${machine_keys[@]}"; do
        local machine_ip
        if ! machine_ip=$(machines_get_ip "$machine_key"); then
            log_warn "Could not resolve IP for machine: $machine_key"
            continue
        fi

        add_a_record "$machine_key" "$machine_ip"
    done
}

# Register DNS server A record pointing to manager IP
register_dns_server_record() {
    log "Registering DNS server A record..."

    # Get manager machine IP
    local manager_ip
    if ! manager_ip=$(machines_get_ip "manager"); then
        log_error "Could not resolve IP for manager machine"
        return 1
    fi

    add_a_record "dns" "$manager_ip"
}

# Discover domain names from Traefik labels in docker-compose files
discover_traefik_domains() {
    local domains=()
    local stacks_dir="${STACKS_DIR:-$PROJECT_ROOT/stacks}"

    # Search all docker-compose.yml files in stacks directory
    while IFS= read -r -d '' compose_file; do
        # Extract Host() rules from Traefik router labels (handle complex rules)
        while IFS= read -r line; do
            # Find all Host(`...`) patterns in the line, including complex rules
            while [[ "$line" =~ Host\(\`([^\`]+)\`\) ]]; do
                local host_rule="${BASH_REMATCH[1]}"
                local matched_pattern="${BASH_REMATCH[0]}"
                # Remove ${BASE_DOMAIN} variable and extract subdomain
                local domain="${host_rule%.\${BASE_DOMAIN\}}"
                if [ -n "$domain" ] && [[ ! " ${domains[*]} " =~ \ ${domain}\  ]]; then
                    domains+=("$domain")
                fi
                # Remove the matched part and continue searching
                line="${line/${matched_pattern}/}"
            done
        done < "$compose_file"
    done < <(find "$stacks_dir" -name "docker-compose.yml" -print0 2>/dev/null || true)

    printf '%s\n' "${domains[@]}"
}

# Register service hostnames as CNAME records pointing to manager
register_service_cnames() {
    log "Registering service CNAME records..."

    # Get actual manager machine hostname using existing functions
    local manager_machine_key
    if ! manager_machine_key=$(machines_parse "manager"); then
        log_error "Could not find manager machine in machines.yaml"
        return 1
    fi

    local manager_hostname
    manager_hostname=$(machines_build_hostname "$manager_machine_key")

    # Discover domains from Traefik labels in docker-compose files
    local discovered_domains
    mapfile -t discovered_domains < <(discover_traefik_domains)

    log "Discovered ${#discovered_domains[@]} domains from Traefik configurations"

    for domain in "${discovered_domains[@]}"; do
        # Skip dns domain (conflicts with DNS server A record)
        if [[ "$domain" != "dns" ]]; then
            add_cname_record "$domain" "$manager_hostname"
        fi
    done
}

# Main configuration function
configure_dns_records() {
    # Wait for DNS server
    if ! wait_for_dns_server; then
        exit 1
    fi

    log "Registering DNS records as per simplified flow:"
    log "  - Machine hostnames → their IPs"
    log "  - DNS server hostname → manager IP"
    log "  - Service hostnames → manager IP (where reverse proxy runs)"

    # Get authentication token
    log "Getting DNS authentication token..."
    if ! DNS_TOKEN=$(get_dns_token); then
        log_error "Failed to authenticate with DNS server"
        return 1
    fi
    export DNS_TOKEN

    # Create base zone (after we have the token)
    create_dns_zone

    # Create _acme-challenge forwarder for Let's Encrypt DNS validation
    create_acme_challenge_forwarder

    # Register machine hostnames to their IPs
    register_machine_dns_records

    # Register DNS server A record pointing to manager
    register_dns_server_record

    # Register service hostnames to manager (via CNAME)
    register_service_cnames

    log "DNS records configuration completed!"
    log "You can access the DNS admin panel at: http://dns.${BASE_DOMAIN:-diyhub.dev}:5380"
    log ""
    log "To use this DNS server, update your network settings to use: $DRIVER_IP as DNS server"
}

# Only run main execution if not being sourced for testing
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Initialize configuration when run as script

    # Check if .env file exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
        log_error ".env file not found. Please copy .env.example to .env and configure it."
        exit 1
    fi

    # Source environment variables
    # shellcheck source=/dev/null
    source "$PROJECT_ROOT/.env"

    # Extract driver machine IP from machines.yaml
    if [ ! -f "$PROJECT_ROOT/machines.yaml" ]; then
        log_error "machines.yaml not found. Cannot determine driver machine IP."
        exit 1
    fi

    # Get driver machine IP (using simplified structure)
    if ! DRIVER_IP=$(machines_get_ip "manager" 2>/dev/null); then
        # Fallback to getting the actual host IP instead of localhost
        DRIVER_IP=$(hostname -I | awk '{print $1}')
        log_warn "Could not get manager IP from machines.yaml, using host IP: $DRIVER_IP"
    fi

    log "Configuring DNS records for ${BASE_DOMAIN:-diyhub.dev}"
    log "Driver machine IP: $DRIVER_IP"

    # Set DNS server URL based on driver IP
    DNS_SERVER_URL="http://${DRIVER_IP}:5380"
    export DNS_SERVER_URL

    # Check if running as part of deployment or standalone
    if [ "${1:-}" = "--auto" ]; then
        configure_dns_records
    else
        log "DNS Records Configuration Script"
        log "================================"
        log ""
        log "This script will:"
        log "1. Create a DNS zone for ${BASE_DOMAIN:-diyhub.dev}"
        log "2. Add A records for all your homelab services"
        log "3. Point all records to your driver machine ($DRIVER_IP)"
        log ""
        read -p "Continue? (y/N): " -r

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            configure_dns_records
        else
            log "Aborted."
        fi
    fi
fi
