#!/bin/bash

# Docker Swarm Monitoring Configuration Script
# Configures Docker daemon metrics and monitoring setup on all Swarm nodes

# Get the actual script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
export PROJECT_ROOT

# Source common utilities
# shellcheck source=scripts/common/ssh.sh
source "$SCRIPT_DIR/../common/ssh.sh"
# shellcheck source=scripts/common/machine.sh
source "$SCRIPT_DIR/../common/machine.sh"

# --- Colors and Logging ---
COLOR_RESET='\033[0m'
COLOR_RED='\033[0;31m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[0;33m'
COLOR_BLUE='\033[0;34m'
COLOR_BOLD='\033[1m'

log() {
  echo -e "${COLOR_BLUE}[INFO]${COLOR_RESET} $1"
}
log_success() {
  echo -e "${COLOR_GREEN}[SUCCESS]${COLOR_RESET} $1"
}
log_warn() {
  echo -e "${COLOR_YELLOW}[WARN]${COLOR_RESET} $1"
}
log_error() {
  echo -e "${COLOR_RED}[ERROR]${COLOR_RESET} $1" >&2
}
log_header() {
  echo -e "\n${COLOR_BOLD}--- $1 ---${COLOR_RESET}"
}

# Configure Docker daemon metrics on a node
# Usage: configure_docker_metrics <machine_name>
configure_docker_metrics() {
  local machine=$1
  local ssh_user ip daemon_config user_host

  ssh_user=$(machines_get_ssh_user "$machine")
  ip=$(machines_get_ip "$machine")

  if [ -z "$ip" ]; then
    log_error "Could not find IP for machine: $machine"
    return 1
  fi

  user_host="${ssh_user}@${ip}"
  log "Configuring Docker daemon metrics on $machine ($ip)..."

  # Check if daemon.json exists
  if ssh_execute "$user_host" "test -f /etc/docker/daemon.json"; then
    log "Reading existing daemon.json on $machine..."
    daemon_config=$(ssh_execute "$user_host" "cat /etc/docker/daemon.json")

    # Check if metrics are already configured
    if echo "$daemon_config" | grep -q "metrics-addr"; then
      log_warn "Metrics already configured on $machine, skipping..."
      return 0
    fi

    # Backup existing config
    log "Backing up existing daemon.json..."
    ssh_execute "$user_host" "sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup"

    # Merge with existing config
    log "Merging metrics configuration with existing settings..."
    local merged_config
    merged_config=$(echo "$daemon_config" | jq '. + {"metrics-addr": "0.0.0.0:9323", "experimental": true}')

    # Write merged config
    echo "$merged_config" | ssh_execute "$user_host" "sudo tee /etc/docker/daemon.json > /dev/null"
  else
    # Create new daemon.json with metrics config
    log "Creating new daemon.json with metrics configuration..."
    ssh_execute "$user_host" 'sudo mkdir -p /etc/docker'
    cat <<'EOF' | ssh_execute "$user_host" "sudo tee /etc/docker/daemon.json > /dev/null"
{
  "metrics-addr": "0.0.0.0:9323",
  "experimental": true
}
EOF
  fi

  # Reload Docker daemon
  log "Reloading Docker daemon on $machine..."
  if ssh_execute "$user_host" "sudo systemctl restart docker"; then
    log_success "Docker daemon reloaded on $machine"

    # Wait for Docker to be ready
    log "Waiting for Docker to be ready..."
    local max_attempts=30
    local attempt=0
    while [ $attempt -lt $max_attempts ]; do
      if ssh_execute "$user_host" "docker info > /dev/null 2>&1"; then
        log_success "Docker is ready on $machine"
        return 0
      fi
      attempt=$((attempt + 1))
      sleep 2
    done

    log_error "Docker failed to become ready on $machine after restart"
    return 1
  else
    log_error "Failed to restart Docker daemon on $machine"
    return 1
  fi
}

# Configure metrics on all Swarm nodes
configure_all_nodes() {
  local config_file="${1:-$PROJECT_ROOT/machines.yaml}"

  if [ ! -f "$config_file" ]; then
    log_error "Configuration file not found: $config_file"
    return 1
  fi

  # Set MACHINES_FILE for functions to use
  export MACHINES_FILE="$config_file"

  log_header "Configuring Docker Metrics on All Swarm Nodes"

  # Get all Swarm nodes
  local machines
  machines=$(machines_parse "swarm")

  if [ -z "$machines" ]; then
    log_error "No Swarm nodes found in configuration"
    return 1
  fi

  local failed_nodes=()

  # Configure each node
  for machine in $machines; do
    if ! configure_docker_metrics "$machine"; then
      failed_nodes+=("$machine")
    fi
  done

  # Report results
  if [ ${#failed_nodes[@]} -eq 0 ]; then
    log_success "All nodes configured successfully"
    return 0
  else
    log_error "Failed to configure metrics on: ${failed_nodes[*]}"
    return 1
  fi
}

# Verify metrics endpoints are accessible
verify_metrics() {
  local config_file="${1:-$PROJECT_ROOT/machines.yaml}"

  # Set MACHINES_FILE for functions to use
  export MACHINES_FILE="$config_file"

  log_header "Verifying Metrics Endpoints"

  local machines
  machines=$(machines_parse "swarm")

  local failed_checks=()

  for machine in $machines; do
    local ip
    ip=$(machines_get_ip "$machine")

    log "Checking Docker metrics endpoint on $machine ($ip:9323)..."
    if curl -sf "http://$ip:9323/metrics" > /dev/null 2>&1; then
      log_success "Docker metrics accessible on $machine"
    else
      log_error "Docker metrics NOT accessible on $machine"
      failed_checks+=("$machine:9323")
    fi

    log "Checking Node Exporter on $machine ($ip:9100)..."
    if curl -sf "http://$ip:9100/metrics" > /dev/null 2>&1; then
      log_success "Node Exporter accessible on $machine"
    else
      log_warn "Node Exporter NOT accessible on $machine (may not be deployed yet)"
    fi
  done

  if [ ${#failed_checks[@]} -eq 0 ]; then
    log_success "All metrics endpoints verified"
    return 0
  else
    log_error "Failed checks: ${failed_checks[*]}"
    return 1
  fi
}

# Main function
main() {
  local command="${1:-}"

  case "$command" in
    configure)
      configure_all_nodes "$@"
      ;;
    verify)
      verify_metrics "$@"
      ;;
    help|--help|-h)
      cat <<EOF
Usage: monitoring.sh <command>

Commands:
  configure    Configure Docker daemon metrics on all Swarm nodes
  verify       Verify metrics endpoints are accessible
  help         Show this help message

Examples:
  monitoring.sh configure    # Configure all nodes
  monitoring.sh verify       # Check metrics endpoints
EOF
      ;;
    *)
      log_error "Unknown command: $command"
      log "Use 'monitoring.sh help' for usage information"
      exit 1
      ;;
  esac
}

# Run main if executed directly (not sourced)
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
  main "$@"
fi
