#!/bin/bash
set -euo pipefail

# Docker Swarm Volume Management
# Handles Docker volume operations for Docker Swarm deployments

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)
PROJECT_ROOT=$(cd -- "$SCRIPT_DIR/../.." && pwd)
STACKS_DIR="$PROJECT_ROOT/stacks"

# Source common utilities
# shellcheck source=../common/ssh.sh
source "$SCRIPT_DIR/../common/ssh.sh"
# shellcheck source=../common/machine.sh
source "$SCRIPT_DIR/../common/machine.sh"

# Colors
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
  echo -e "
${COLOR_BOLD}--- $1 ---${COLOR_RESET}"
}

# List Docker volumes
# Usage: volume_ls [service_name]
#   service_name (optional): Filter volumes by service/stack name
volume_ls() {
  local service_filter="${1:-}"

  log_header "DOCKER VOLUMES"

  if [ -z "$service_filter" ]; then
    # List all volumes
    log "Listing all Docker volumes:"
    docker volume ls --format "table {{.Driver}}\t{{.Name}}\t{{.Scope}}"
  else
    # Filter volumes by service/stack name
    log "Listing volumes for service: $service_filter"
    docker volume ls --filter "name=${service_filter}" --format "table {{.Driver}}\t{{.Name}}\t{{.Scope}}"
  fi
}

# Inspect volumes for a specific service
# Usage: volume_inspect <service_name>
#   service_name (required): Service/stack name to inspect volumes for
volume_inspect() {
  local service="${1:-}"

  if [ -z "$service" ]; then
    log_error "Service name is required"
    log "Usage: volume inspect <service_name>"
    exit 1
  fi

  log_header "VOLUME INSPECTION: $service"

  # Find volumes matching the service name
  local volumes
  volumes=$(docker volume ls --filter "name=${service}" --format "{{.Name}}" || true)

  if [ -z "$volumes" ]; then
    log_warn "No volumes found for service: $service"
    exit 0
  fi

  # Inspect each volume
  while IFS= read -r volume; do
    log "Volume: $volume"
    docker volume inspect "$volume" --format '  Driver: {{.Driver}}
  Mountpoint: {{.Mountpoint}}
  Options: {{json .Options}}'
    echo ""
  done <<< "$volumes"
}

# Compare volume configuration between compose file and actual Docker volumes
# Usage: volume_diff <service_name>
#   service_name (required): Service/stack name to compare volumes for
volume_diff() {
  local service="${1:-}"

  if [ -z "$service" ]; then
    log_error "Service name is required"
    log "Usage: volume diff <service_name>"
    exit 1
  fi

  log_header "VOLUME DIFF: $service"

  # Find the service's compose file
  local compose_file="$STACKS_DIR/apps/$service/docker-compose.yml"

  if [ ! -f "$compose_file" ]; then
    log_error "Compose file not found: $compose_file"
    exit 1
  fi

  log "Comparing volumes for service: $service"
  log "Compose file: $compose_file"
  echo ""

  # Find volumes matching the service name
  local volumes
  volumes=$(docker volume ls --filter "name=${service}" --format "{{.Name}}" || true)

  if [ -z "$volumes" ]; then
    log_warn "No volumes found for service: $service"
    log "Check if the service has been deployed and has volumes defined."
    exit 0
  fi

  # Check each volume
  local has_diff=false
  while IFS= read -r volume; do
    log "Checking volume: ${COLOR_BOLD}$volume${COLOR_RESET}"

    # Get current volume configuration
    local current_driver current_options
    current_driver=$(docker volume inspect "$volume" --format '{{.Driver}}')
    current_options=$(docker volume inspect "$volume" --format '{{json .Options}}')

    echo "  Current driver: $current_driver"
    echo "  Current options: $current_options"

    # Parse compose file to check if volume is defined
    if grep -q "^  $volume:" "$compose_file" 2>/dev/null || grep -q "^    ${volume##*_}:" "$compose_file" 2>/dev/null; then
      log_success "Volume definition found in compose file"
    else
      log_warn "Volume not explicitly defined in compose file (using defaults)"
    fi

    echo ""
  done <<< "$volumes"

  if [ "$has_diff" = false ]; then
    log_success "All volumes are using Docker defaults or have matching configurations"
  fi
}

# Recreate volumes for a service (useful when volume config changes)
# Usage: volume_recreate <service_name> [--force] [--backup] [--backup-dir <dir>]
#   service_name (required): Service/stack name to recreate volumes for
#   --force: Skip confirmation prompt
#   --backup: Create backup before removing volumes
#   --backup-dir: Custom backup directory (default: /tmp/volume-backups)
volume_recreate() {
  local service=""
  local force=false
  local backup=false
  local backup_dir="/tmp/volume-backups"

  # Parse arguments
  while [[ $# -gt 0 ]]; do
    case $1 in
      --force)
        force=true
        shift
        ;;
      --backup)
        backup=true
        shift
        ;;
      --backup-dir)
        backup_dir="$2"
        shift 2
        ;;
      *)
        if [ -z "$service" ]; then
          service="$1"
        else
          log_error "Unknown argument: $1"
          exit 1
        fi
        shift
        ;;
    esac
  done

  if [ -z "$service" ]; then
    log_error "Service name is required"
    log "Usage: volume recreate <service_name> [--force] [--backup] [--backup-dir <dir>]"
    exit 1
  fi

  log_header "VOLUME RECREATE: $service"

  # Find the service's compose file
  local compose_file="$STACKS_DIR/apps/$service/docker-compose.yml"

  if [ ! -f "$compose_file" ]; then
    log_error "Compose file not found: $compose_file"
    exit 1
  fi

  # Find volumes matching the service name
  local volumes
  volumes=$(docker volume ls --filter "name=${service}" --format "{{.Name}}" || true)

  if [ -z "$volumes" ]; then
    log_warn "No volumes found for service: $service"
    exit 0
  fi

  # Show what will be recreated
  log "Volumes to recreate:"
  echo "$volumes" | while IFS= read -r volume; do
    echo "  - $volume"
  done
  echo ""

  # Confirmation prompt unless --force
  if [ "$force" = false ]; then
    log_warn "This will:"
    echo "  1. Stop the service stack: $service"
    echo "  2. Remove volumes: $(echo "$volumes" | wc -l) volume(s)"
    echo "  3. Redeploy the service (volumes will be recreated with new config)"
    echo ""

    if [ "$backup" = true ]; then
      log "Backups will be saved to: $backup_dir"
    else
      log_warn "NO BACKUP will be created (use --backup to enable)"
    fi

    echo ""
    read -p "Continue? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
      log "Aborted."
      exit 0
    fi
  fi

  # Step 1: Create backups if requested
  if [ "$backup" = true ]; then
    log "Creating backups..."
    mkdir -p "$backup_dir"

    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)

    echo "$volumes" | while IFS= read -r volume; do
      local backup_file="$backup_dir/${volume}_${timestamp}.tar.gz"
      log "Backing up $volume to $backup_file"

      # Create backup using docker run with volume mounted
      docker run --rm -v "$volume:/data" -v "$backup_dir:/backup" alpine tar czf "/backup/$(basename "$backup_file")" -C /data . 2>/dev/null || {
        log_warn "Failed to backup $volume (volume may be empty or inaccessible)"
      }
    done

    log_success "Backups completed"
    echo ""
  fi

  # Step 2: Stop the service
  log "Stopping service stack: $service"
  docker stack rm "$service" || {
    log_error "Failed to remove stack: $service"
    exit 1
  }

  # Wait for service to stop
  log "Waiting for service to stop..."
  sleep 5

  # Step 3: Remove volumes
  log "Removing volumes..."
  echo "$volumes" | while IFS= read -r volume; do
    log "Removing volume: $volume"
    docker volume rm "$volume" || log_warn "Failed to remove volume: $volume"
  done

  log_success "Volumes removed"
  echo ""

  # Step 4: Redeploy the service
  log "Redeploying service: $service"
  log "Run: ./selfhosted.sh deploy --skip-infra --only-apps $service"
  log "This will recreate volumes with the new configuration from docker-compose.yml"

  if [ "$backup" = true ]; then
    echo ""
    log_success "Backups saved to: $backup_dir"
  fi
}
