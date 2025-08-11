#!/bin/bash
# Simple Homelab Configuration Validator
# Basic validation without external dependencies

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEFAULT_CONFIG="$PROJECT_ROOT/homelab.yaml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

# Usage information
usage() {
    cat << EOF
Usage: $0 [CONFIG_FILE]

Simple validation for homelab.yaml configuration.

ARGUMENTS:
    CONFIG_FILE         Path to homelab.yaml file (default: homelab.yaml)

EXAMPLES:
    $0                                  # Validate default homelab.yaml
    $0 examples/homelab-basic.yaml     # Validate specific example

EOF
}

# Validate file exists and is readable
validate_file_access() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        log_error "Configuration file not found: $file"
        return 1
    fi

    if [[ ! -r "$file" ]]; then
        log_error "Configuration file not readable: $file"
        return 1
    fi

    return 0
}

# Validate YAML syntax
validate_yaml_syntax() {
    local config_file="$1"

    log_info "Checking YAML syntax..."

    if ! yq . "$config_file" >/dev/null 2>&1; then
        log_error "Invalid YAML syntax in $config_file"
        return 1
    fi

    log_success "YAML syntax is valid"
    return 0
}

# Validate required fields
validate_required_fields() {
    local config_file="$1"
    local errors=0

    log_info "Checking required fields..."

    # Check version
    local version
    version=$(yq '.version' "$config_file" 2>/dev/null | tr -d '"')
    if [[ "$version" != "2.0" ]]; then
        log_error "Missing or invalid version field (expected '2.0')"
        ((errors++))
    fi

    # Check deployment
    local deployment
    deployment=$(yq '.deployment' "$config_file" 2>/dev/null | tr -d '"')
    if [[ ! "$deployment" =~ ^(docker_compose|docker_swarm|kubernetes)$ ]]; then
        log_error "Missing or invalid deployment field (expected 'docker_compose', 'docker_swarm', or 'kubernetes')"
        ((errors++))
    fi

    # Check services exist
    local services_count
    services_count=$(yq '.services | length' "$config_file" 2>/dev/null)
    if [[ "$services_count" -eq 0 ]]; then
        log_error "No services defined (at least one service required)"
        ((errors++))
    fi

    return $errors
}

# Validate service definitions
validate_services() {
    local config_file="$1"
    local errors=0

    log_info "Validating service definitions..."

    # Get all service names
    local services
    services=$(yq '.services | keys | .[]' "$config_file" 2>/dev/null | tr -d '"')

    while read -r service; do
        if [[ -n "$service" ]]; then
            # Check image field (required)
            local image
            image=$(yq ".services.$service.image" "$config_file" 2>/dev/null)
            if [[ -z "$image" || "$image" == "null" ]]; then
                log_error "Service '$service' missing required 'image' field"
                ((errors++))
            fi

            # Check port vs ports conflict
            local port
            local ports
            port=$(yq ".services.$service.port" "$config_file" 2>/dev/null)
            ports=$(yq ".services.$service.ports" "$config_file" 2>/dev/null)

            if [[ "$port" != "null" && "$ports" != "null" ]]; then
                log_error "Service '$service' cannot have both 'port' and 'ports' fields"
                ((errors++))
            fi
        fi
    done <<< "$services"

    return $errors
}

# Validate machine references
validate_machine_references() {
    local config_file="$1"
    local errors=0

    log_info "Validating machine references..."

    # Get machine names
    local machine_names
    machine_names=$(yq '.machines | keys | .[]' "$config_file" 2>/dev/null | tr -d '"')

    # Get deploy targets that are not standard keywords
    local services
    services=$(yq '.services | keys | .[]' "$config_file" 2>/dev/null | tr -d '"')

    while read -r service; do
        if [[ -n "$service" ]]; then
            local deploy_target
            deploy_target=$(yq ".services.$service.deploy" "$config_file" 2>/dev/null | tr -d '"')

            if [[ -n "$deploy_target" && "$deploy_target" != "null" ]]; then
                # Check if deploy target is a standard keyword
                if [[ ! "$deploy_target" =~ ^(driver|all|random|any)$ ]]; then
                    # Check if it matches a machine name
                    if ! echo "$machine_names" | grep -q "^$deploy_target$"; then
                        log_error "Service '$service' deploy target '$deploy_target' does not match any machine name"
                        ((errors++))
                    fi
                fi
            fi
        fi
    done <<< "$services"

    return $errors
}

# Main validation function
main() {
    local config_file="${1:-$DEFAULT_CONFIG}"

    log_info "Starting homelab.yaml validation for: $config_file"

    # Validate file access
    validate_file_access "$config_file" || exit 1

    # Validate YAML syntax
    validate_yaml_syntax "$config_file" || exit 1

    # Validate required fields
    validate_required_fields "$config_file"
    local field_errors=$?

    # Validate services
    validate_services "$config_file"
    local service_errors=$?

    # Validate machine references
    validate_machine_references "$config_file"
    local machine_errors=$?

    local total_errors=$((field_errors + service_errors + machine_errors))

    if [[ $total_errors -gt 0 ]]; then
        log_error "Validation failed with $total_errors errors"
        exit 1
    fi

    log_success "homelab.yaml validation completed successfully"

    # Show summary
    echo
    log_info "Configuration summary:"
    echo "  Deployment type: $(yq '.deployment' "$config_file")"
    echo "  Machines: $(yq '.machines | length' "$config_file" 2>/dev/null || echo "0")"
    echo "  Services: $(yq '.services | length' "$config_file")"
}

# Parse command line arguments
if [[ $# -gt 1 ]]; then
    usage >&2
    exit 1
fi

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
