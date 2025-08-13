#!/bin/bash

# SSH-based Docker Compose Bundle Deployment Engine
# Coordinates deployment of Docker Compose bundles across multiple machines
# Part of Issue #37 - SSH-based Deployment Engine

set -e

# Get script directory for relative path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source required dependencies
# shellcheck disable=SC1091
source "$SCRIPT_DIR/ssh.sh"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/translate_homelab_to_compose.sh"

# Default configuration
HOMELAB_CONFIG="${HOMELAB_CONFIG:-$PROJECT_ROOT/homelab.yaml}"
BUNDLES_DIR="${BUNDLES_DIR:-$PROJECT_ROOT/bundles}"
REMOTE_DEPLOY_PATH="${REMOTE_DEPLOY_PATH:-/opt/homelab}"

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

# Function: get_all_machines
# Description: Gets all machine names from homelab.yaml
# Arguments: $1 - config file path
# Returns: List of machine names (one per line)
get_all_machines() {
    local config_file="${1:-$HOMELAB_CONFIG}"

    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi

    yq '.machines | keys | .[]' "$config_file" 2>/dev/null | tr -d '"'
}

# Function: get_machine_connection_info
# Description: Gets host and user info for a specific machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: Outputs "host user" format
get_machine_connection_info() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    local host user
    host=$(yq ".machines[\"$machine_name\"].host" "$config_file" 2>/dev/null | tr -d '"')
    user=$(yq ".machines[\"$machine_name\"].user" "$config_file" 2>/dev/null | tr -d '"')

    if [[ "$host" == "null" || "$user" == "null" ]]; then
        log_error "Invalid machine configuration for: $machine_name"
        return 1
    fi

    echo "$host $user"
}

# Function: test_machine_connectivity
# Description: Tests SSH connectivity to a machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: 0 if successful, 1 if failed
test_machine_connectivity() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Testing connectivity to $machine_name..."

    local connection_info
    connection_info=$(get_machine_connection_info "$machine_name" "$config_file") || return 1

    local host user
    read -r host user <<< "$connection_info"

    if ssh_test_connection "$user@$host"; then
        log_success "Successfully connected to $machine_name ($host)"
        return 0
    else
        log_error "Failed to connect to $machine_name ($host)"
        return 1
    fi
}

# Function: copy_bundle_to_machine
# Description: Copies Docker Compose bundle to remote machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: 0 on success, 1 on failure
copy_bundle_to_machine() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Copying bundle to $machine_name..."

    # Check if bundle exists
    local bundle_dir="$BUNDLES_DIR/$machine_name"
    if [[ ! -d "$bundle_dir" ]]; then
        log_error "Bundle directory not found: $bundle_dir"
        return 1
    fi

    # Get connection info
    local connection_info
    connection_info=$(get_machine_connection_info "$machine_name" "$config_file") || return 1

    local host user
    read -r host user <<< "$connection_info"

    # Create remote directory
    ssh_execute "$user@$host" "mkdir -p $REMOTE_DEPLOY_PATH" || {
        log_error "Failed to create remote directory on $machine_name"
        return 1
    }

    # Copy docker-compose.yaml
    if [[ -f "$bundle_dir/docker-compose.yaml" ]]; then
        scp "$bundle_dir/docker-compose.yaml" "$user@$host:$REMOTE_DEPLOY_PATH/" || {
            log_error "Failed to copy docker-compose.yaml to $machine_name"
            return 1
        }
    fi

    # Copy nginx configuration if exists
    if [[ -d "$bundle_dir/nginx" ]]; then
        scp -r "$bundle_dir/nginx" "$user@$host:$REMOTE_DEPLOY_PATH/" || {
            log_error "Failed to copy nginx configuration to $machine_name"
            return 1
        }
    fi

    # Copy environment file if exists
    if [[ -f "$PROJECT_ROOT/.env" ]]; then
        scp "$PROJECT_ROOT/.env" "$user@$host:$REMOTE_DEPLOY_PATH/" 2>/dev/null || true
    fi

    log_success "Bundle copied to $machine_name"
    return 0
}

# Function: deploy_bundle_on_machine
# Description: Executes deployment commands on remote machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: 0 on success, 1 on failure
deploy_bundle_on_machine() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Deploying bundle on $machine_name..."

    # Get connection info
    local connection_info
    connection_info=$(get_machine_connection_info "$machine_name" "$config_file") || return 1

    local host user
    read -r host user <<< "$connection_info"

    # Execute deployment commands
    ssh_execute "$user@$host" "cd $REMOTE_DEPLOY_PATH && docker compose down --remove-orphans" || {
        log_warning "Failed to stop existing services on $machine_name (may be first deployment)"
    }

    ssh_execute "$user@$host" "cd $REMOTE_DEPLOY_PATH && docker compose pull" || {
        log_warning "Failed to pull images on $machine_name"
    }

    ssh_execute "$user@$host" "cd $REMOTE_DEPLOY_PATH && docker compose up -d" || {
        log_error "Failed to start services on $machine_name"
        return 1
    }

    log_success "Bundle deployed on $machine_name"
    return 0
}

# Function: verify_deployment_on_machine
# Description: Verifies that services are running on remote machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: 0 on success, 1 on failure
verify_deployment_on_machine() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Verifying deployment on $machine_name..."

    # Get connection info
    local connection_info
    connection_info=$(get_machine_connection_info "$machine_name" "$config_file") || return 1

    local host user
    read -r host user <<< "$connection_info"

    # Check service status
    local status
    status=$(ssh_execute "$user@$host" "cd $REMOTE_DEPLOY_PATH && docker compose ps --format table" 2>/dev/null) || {
        log_warning "Could not verify service status on $machine_name"
        return 1
    }

    log_info "Services on $machine_name:"
    echo "$status"

    return 0
}

# Function: deploy_to_single_machine
# Description: Performs complete deployment to a single machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: 0 on success, 1 on failure
deploy_to_single_machine() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Starting deployment to $machine_name..."

    # Test connectivity first
    test_machine_connectivity "$machine_name" "$config_file" || return 1

    # Copy bundle
    copy_bundle_to_machine "$machine_name" "$config_file" || return 1

    # Deploy bundle
    deploy_bundle_on_machine "$machine_name" "$config_file" || return 1

    # Verify deployment
    verify_deployment_on_machine "$machine_name" "$config_file" || return 1

    log_success "Deployment to $machine_name completed successfully"
    return 0
}

# Function: deploy_to_all_machines
# Description: Deploys bundles to all machines in configuration
# Arguments: $1 - config file path, $2+ - optional flags (--dry-run, --progress)
# Returns: 0 on success, 1 on failure
deploy_to_all_machines() {
    local config_file="${1:-$HOMELAB_CONFIG}"
    shift

    # Parse flags
    local dry_run=false
    local show_progress=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                dry_run=true
                shift
                ;;
            --progress)
                show_progress=true
                shift
                ;;
            *)
                shift
                ;;
        esac
    done

    log_info "Deploying to all machines$([ "$dry_run" = true ] && echo " (dry run)")"

    # Validate configuration
    if [[ ! -f "$config_file" ]]; then
        log_error "Configuration file not found: $config_file"
        return 1
    fi

    # Generate bundles if missing
    if [[ ! -d "$BUNDLES_DIR" ]]; then
        log_info "Generating bundles before deployment..."
        translate_homelab_to_compose -c "$config_file" -o "$BUNDLES_DIR" || {
            log_error "Failed to generate bundles"
            return 1
        }
    fi

    # Get all machines
    local machines
    machines=$(get_all_machines "$config_file") || return 1

    local machine_count
    machine_count=$(echo "$machines" | wc -l)
    local current=0

    # Deploy to each machine
    while IFS= read -r machine; do
        [[ -z "$machine" ]] && continue

        current=$((current + 1))

        if [[ "$show_progress" == true ]]; then
            log_info "Progress: $current/$machine_count - $machine"
        fi

        if [[ "$dry_run" == true ]]; then
            log_info "Would deploy to $machine"
        else
            deploy_to_single_machine "$machine" "$config_file" || {
                log_error "Failed to deploy to $machine"
                return 1
            }
        fi
    done <<< "$machines"

    log_success "Deployment to all machines completed successfully"
    return 0
}

# Function: check_deployment_status
# Description: Checks deployment status across all machines
# Arguments: $1 - config file path
# Returns: 0 on success, 1 on failure
check_deployment_status() {
    local config_file="${1:-$HOMELAB_CONFIG}"

    log_info "Checking deployment status across all machines..."

    local machines
    machines=$(get_all_machines "$config_file") || return 1

    while IFS= read -r machine; do
        [[ -z "$machine" ]] && continue

        echo "🔍 Checking $machine..."
        verify_deployment_on_machine "$machine" "$config_file" || true
        echo
    done <<< "$machines"

    return 0
}

# Function: deploy_with_dependencies
# Description: Deploys services with dependency ordering
# Arguments: $1 - config file path
# Returns: 0 on success, 1 on failure
deploy_with_dependencies() {
    local config_file="${1:-$HOMELAB_CONFIG}"

    log_info "Analyzing deployment dependencies..."

    # For now, just deploy to all machines (dependency logic can be enhanced later)
    deploy_to_all_machines "$config_file"
}

# Function: rollback_deployment
# Description: Rolls back deployment on a machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: 0 on success, 1 on failure
rollback_deployment() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Rolling back deployment on $machine_name..."

    # Get connection info
    local connection_info
    connection_info=$(get_machine_connection_info "$machine_name" "$config_file") || return 1

    local host user
    read -r host user <<< "$connection_info"

    # Stop all services
    ssh_execute "$user@$host" "cd $REMOTE_DEPLOY_PATH && docker compose down" || {
        log_error "Failed to rollback deployment on $machine_name"
        return 1
    }

    log_success "Rollback completed on $machine_name"
    return 0
}

# Function: deploy_to_specific_machines
# Description: Deploys to only specified machines
# Arguments: $1 - machine names (space separated), $2 - config file path
# Returns: 0 on success, 1 on failure
deploy_to_specific_machines() {
    local machine_names="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Deploying to specific machines: $machine_names"

    for machine in $machine_names; do
        deploy_to_single_machine "$machine" "$config_file" || {
            log_error "Failed to deploy to $machine"
            return 1
        }
    done

    log_success "Deployment to specific machines completed"
    return 0
}

# Function: filter_machines_by_role
# Description: Filters machines by role using homelab.yaml configuration
# Arguments: $1 - role name, $2 - config file path
# Returns: List of machines with specified role
filter_machines_by_role() {
    local role="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    # Simple implementation using yq to filter by role
    yq ".machines | to_entries[] | select(.value.role == \"$role\") | .key" "$config_file" 2>/dev/null || get_all_machines "$config_file"
}

# Function: filter_machines_by_labels
# Description: Filters machines by labels using homelab.yaml configuration
# Arguments: $1 - label name, $2 - config file path
# Returns: List of machines with specified label
filter_machines_by_labels() {
    local label="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    # Simple implementation using yq to filter by labels
    yq ".machines | to_entries[] | select(.value.labels[]? | contains(\"$label\")) | .key" "$config_file" 2>/dev/null || get_all_machines "$config_file"
}

# Function: collect_deployment_logs
# Description: Collects deployment logs from a machine
# Arguments: $1 - machine name, $2 - config file path
# Returns: 0 on success, 1 on failure
collect_deployment_logs() {
    local machine_name="$1"
    local config_file="${2:-$HOMELAB_CONFIG}"

    log_info "Collecting deployment logs from $machine_name..."

    # Get connection info
    local connection_info
    connection_info=$(get_machine_connection_info "$machine_name" "$config_file") || return 1

    local host user
    read -r host user <<< "$connection_info"

    # Get logs
    ssh_execute "$user@$host" "cd $REMOTE_DEPLOY_PATH && docker compose logs --tail=50" || {
        log_warning "Failed to collect logs from $machine_name"
        return 1
    }

    return 0
}

# Function: usage
# Description: Shows usage information
# Arguments: None
# Returns: None
usage() {
    cat <<EOF
SSH-based Docker Compose Bundle Deployment Engine

USAGE:
    $0 [COMMAND] [OPTIONS]

COMMANDS:
    deploy-all [CONFIG]           Deploy to all machines
    deploy [MACHINE] [CONFIG]     Deploy to specific machine
    status [CONFIG]               Check deployment status
    rollback [MACHINE] [CONFIG]   Rollback deployment
    test-connectivity [CONFIG]    Test SSH connectivity
    logs [MACHINE] [CONFIG]       Collect deployment logs

OPTIONS:
    --dry-run                     Show what would be deployed
    --progress                    Show deployment progress
    -h, --help                    Show this help message

EXAMPLES:
    $0 deploy-all homelab.yaml                    # Deploy to all machines
    $0 deploy driver homelab.yaml                 # Deploy to driver machine
    $0 deploy-all homelab.yaml --dry-run          # Dry run deployment
    $0 status homelab.yaml                        # Check all machine status
    $0 rollback driver homelab.yaml               # Rollback driver deployment

DESCRIPTION:
    Coordinates deployment of Docker Compose bundles across multiple machines
    using SSH. Requires bundles to be generated first by translate_homelab_to_compose.sh.

EOF
}

# Main function for command-line usage
main() {
    local command="$1"
    shift

    case "$command" in
        deploy-all)
            deploy_to_all_machines "$@"
            ;;
        deploy)
            local machine="$1"
            local config="${2:-$HOMELAB_CONFIG}"
            deploy_to_single_machine "$machine" "$config"
            ;;
        status)
            check_deployment_status "$@"
            ;;
        rollback)
            rollback_deployment "$@"
            ;;
        test-connectivity)
            local config="${1:-$HOMELAB_CONFIG}"
            local machines
            machines=$(get_all_machines "$config")
            while IFS= read -r machine; do
                [[ -z "$machine" ]] && continue
                test_machine_connectivity "$machine" "$config"
            done <<< "$machines"
            ;;
        logs)
            collect_deployment_logs "$@"
            ;;
        -h|--help|help)
            usage
            exit 0
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Only run main if script is executed directly (not sourced)
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
