#!/bin/bash
set -euo pipefail

# --- Configuration ---
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]:-}")" && pwd)
PROJECT_ROOT=${PROJECT_ROOT:-"$SCRIPT_DIR"}
STACKS_DIR="$PROJECT_ROOT/stacks"
APPS_DIR="$STACKS_DIR/apps"
REVERSE_PROXY_DIR="$STACKS_DIR/reverse-proxy"
MONITORING_DIR="$STACKS_DIR/monitoring"
DNS_DIR="$STACKS_DIR/dns"
NETWORK_NAME="traefik-public"
MACHINES_FILE="$PROJECT_ROOT/machines.yaml"


# --- Dependencies ---
if [ -z "${TEST:-}" ]; then
  # shellcheck source=scripts/ssh.sh
  source "${PROJECT_ROOT}/scripts/ssh.sh"
fi

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
  echo -e "
${COLOR_BOLD}--- $1 ---${COLOR_RESET}"
}

# --- ASCII Art Banner ---
show_banner() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}"
  cat << 'EOF'
 ███████ ███████ ██      ███████ ██   ██  ██████  ███████ ████████ ███████ ██████      ███████ ██   ██
 ██      ██      ██      ██      ██   ██ ██    ██ ██         ██    ██      ██   ██     ██      ██   ██
 ███████ █████   ██      █████   ███████ ██    ██ ███████    ██    █████   ██   ██     ███████ ███████
      ██ ██      ██      ██      ██   ██ ██    ██      ██    ██    ██      ██   ██          ██ ██   ██
 ███████ ███████ ███████ ██      ██   ██  ██████  ███████    ██    ███████ ██████  ██  ███████ ██   ██

EOF
  echo -e "${COLOR_GREEN}"
  cat << 'EOF'
   🏠 HOMELAB DEPLOYMENT AUTOMATION 🚀
   ═══════════════════════════════════════
   Docker Swarm • Container Management
   Network Configuration • SSL Automation
   Multi-Node Orchestration • Self-Healing
   ═══════════════════════════════════════

EOF
  echo -e "${COLOR_RESET}"
}

show_compact_banner() {
  echo -e "${COLOR_BOLD}${COLOR_BLUE}🏠 SELFHOSTED HOMELAB 🚀${COLOR_RESET} ${COLOR_GREEN}Deploy • Manage • Scale${COLOR_RESET}"
  echo -e "${COLOR_YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${COLOR_RESET}"
}

# --- Helper Functions ---

check_dependencies() {
  local missing=0
  for cmd in docker ssh yq; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      log_error "Required command '$cmd' is not installed."
      missing=1
    fi
  done
  if [ "$missing" -eq 1 ]; then
    log_error "Please install missing dependencies and try again."
    exit 1
  fi
}

check_configs() {
  if ! [ -f "$MACHINES_FILE" ]; then
    log_error "machines.yaml not found in $PROJECT_ROOT"
    log_error "An example is available in $PROJECT_ROOT/machines.yaml.example"
    exit 1
  fi
  if ! [ -f "$PROJECT_ROOT/.env" ]; then
    log_error ".env not found in $PROJECT_ROOT"
    log_error "An example is available in $PROJECT_ROOT/.env.example"
    exit 1
  fi
}

# --- NUKE Functionality ---

nuke_cluster() {
  log_header "NUKE: DESTROYING HOMELAB CLUSTER"



  read -p "Are you absolutely sure you want to destroy the entire cluster? This is irreversible. (y/N): " -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Nuke aborted."
    exit 0
  fi

  check_configs
  source "$PROJECT_ROOT/.env"
  source "$PROJECT_ROOT/scripts/machines.sh"

  log "Reading node information from $MACHINES_FILE..."
  local nodes=()
  while IFS= read -r line; do
    nodes+=("$line")
  done < <(yq -r '.machines[] | .ssh_user + "@" + .ip' "$MACHINES_FILE")

  log_header "Step 1: Removing all Docker stacks"
  local stacks
  stacks=$(docker stack ls --format '{{.Name}}' 2>/dev/null || true)
  if [ -z "$stacks" ]; then
    log "No stacks found to remove."
  else
    for stack in $stacks; do
      log "Removing stack: ${COLOR_YELLOW}$stack${COLOR_RESET}"
      docker stack rm "$stack"
    done
    log "Waiting for stacks to be removed..."
    sleep 10
  fi

  log_header "Step 2: Removing custom overlay networks"
  local networks
  networks=$(docker network ls --filter driver=overlay --format '{{.Name}}' 2>/dev/null | grep -v ingress || true)
  if [ -z "$networks" ]; then
    log "No custom overlay networks found."
  else
    for net in $networks; do
      log "Removing network: ${COLOR_YELLOW}$net${COLOR_RESET}"
      docker network rm "$net"
    done
  fi

  log_header "Step 3: Removing storage volumes from all nodes"
  local homelab_volumes=()
  # Find all docker-compose.yml files in the apps directory
  for compose_file in "$APPS_DIR"/*/docker-compose.yml; do
    if [ -f "$compose_file" ]; then
      # The project name is the name of the directory containing the compose file
      local project_name
      project_name=$(basename "$(dirname "$compose_file")")
      # Extract volume names from the compose file
      local volumes
      volumes=$(yq '(.volumes // {}) | keys | .[]' "$compose_file" | tr -d '"')
      for vol in $volumes; do
        # Docker compose prepends the project name to the volume name
        homelab_volumes+=("${project_name}_${vol}")
      done
    fi
  done

  if [ ${#homelab_volumes[@]} -eq 0 ]; then
    log "No named volumes found in any app's docker-compose.yml file."
  else
    log "Found the following homelab volumes to remove:"
    for vol in "${homelab_volumes[@]}"; do
      log "  - $vol"
    done

    log "Removing volumes from all nodes..."
    local current_machine_ip
    current_machine_ip=$(machines_my_ip)

    for node in "${nodes[@]}"; do
      log "  - Checking node: ${COLOR_YELLOW}$node${COLOR_RESET}"

      # Extract IP from user@ip format
      local node_ip="${node##*@}"

      # Check if this is the local machine
      if [[ "$node_ip" == "$current_machine_ip" || "$node_ip" == "localhost" || "$node_ip" == "127.0.0.1" ]]; then
        log "    - Running locally (detected as current machine)"
        for vol in "${homelab_volumes[@]}"; do
          if docker volume inspect "$vol" &>/dev/null; then
            log "    - Removing volume $vol locally"
            docker volume rm --force "$vol" || true
          fi
        done
      else
        # Remote machine - use SSH
        # First, check if the node is even reachable
        if ! ssh_execute "$node" "exit 0" &>/dev/null; then
            log_warn "    - Could not connect to node $node. Skipping."
            continue # Skip to the next node
        fi

        for vol in "${homelab_volumes[@]}"; do
          if ssh_execute "$node" "docker volume inspect $vol &>/dev/null"; then
            log "    - Removing volume $vol from $node"
            ssh_execute "$node" "docker volume rm --force $vol" || true
          fi
        done
      fi
    done
  fi

  log_header "Step 4: Dismantling the Swarm"
  log "Forcing all nodes to leave the swarm..."
  local current_machine_ip
  current_machine_ip=$(machines_my_ip)

  for node in "${nodes[@]}"; do
    log "  - Cleaning node: ${COLOR_YELLOW}$node${COLOR_RESET}"

    # Extract IP from user@ip format
    local node_ip="${node##*@}"

    # Check if this is the local machine
    if [[ "$node_ip" == "$current_machine_ip" || "$node_ip" == "localhost" || "$node_ip" == "127.0.0.1" ]]; then
      log "    - Running locally (detected as current machine)"
      docker swarm leave --force || true
    else
      # Remote machine - use SSH
      ssh "$node" "docker swarm leave --force" || true
    fi
  done

    log_success "Nuke complete. The swarm cluster has been destroyed."
}

_remove_service_volumes() {
  echo "APPS_DIR is: $APPS_DIR" >&2
  local stack_name="$1"
  local compose_file=""

  # Find the compose file for the given stack
  if [ -f "$APPS_DIR/$stack_name/docker-compose.yml" ]; then
    compose_file="$APPS_DIR/$stack_name/docker-compose.yml"
  elif [ "$stack_name" == "reverse-proxy" ] && [ -f "$REVERSE_PROXY_DIR/docker-compose.yml" ]; then
    compose_file="$REVERSE_PROXY_DIR/docker-compose.yml"
  elif [ "$stack_name" == "monitoring" ] && [ -f "$MONITORING_DIR/docker-compose.yml" ]; then
    compose_file="$MONITORING_DIR/docker-compose.yml"
  elif [ "$stack_name" == "dns" ] && [ -f "$DNS_DIR/docker-compose.yml" ]; then
    compose_file="$DNS_DIR/docker-compose.yml"
  else
    log_warn "No compose file found for service '$stack_name' in standard locations. Skipping volume removal."
    return
  fi

  log_header "VOLUMES: Removing volumes for service: ${COLOR_YELLOW}$stack_name${COLOR_RESET}"
  local homelab_volumes=()
  local project_name="$stack_name"
  local volumes
  volumes=$(yq '(.volumes // {}) | keys | .[]' "$compose_file" | tr -d '"')

  if [ -z "$volumes" ]; then
    log "No named volumes found in $compose_file."
    return
  fi

  for vol in $volumes; do
    homelab_volumes+=("${project_name}_${vol}")
  done

  log "Found the following volumes to remove for service '$stack_name':"
  for vol in "${homelab_volumes[@]}"; do
    log "  - $vol"
  done

  log "Removing volumes from all nodes..."
  local nodes=()
  while IFS= read -r line; do
    nodes+=("$line")
  done < <(yq -r '.machines[] | .ssh_user + "@" + .ip' "$MACHINES_FILE")

  for node in "${nodes[@]}"; do
    log "  - Checking node: ${COLOR_YELLOW}$node${COLOR_RESET}"
    if ! ssh_execute "$node" "exit 0" &>/dev/null; then
        log_warn "    - Could not connect to node $node. Skipping volume removal on this node."
        continue
    fi

    for vol in "${homelab_volumes[@]}"; do
      if ssh_execute "$node" "docker volume inspect $vol &>/dev/null"; then
        log "    - Removing volume $vol from $node"
        ssh_execute "$node" "docker volume rm --force $vol"
      else
        log "    - Volume $vol not found on $node, skipping."
      fi
    done
  done
}

nuke_single_service() {
  local stack_name="$1"
  local compose_file=""

  # Find the compose file for the given stack
  if [ -f "$APPS_DIR/$stack_name/docker-compose.yml" ]; then
    compose_file="$APPS_DIR/$stack_name/docker-compose.yml"
  elif [ "$stack_name" == "reverse-proxy" ] && [ -f "$REVERSE_PROXY_DIR/docker-compose.yml" ]; then
    compose_file="$REVERSE_PROXY_DIR/docker-compose.yml"
  elif [ "$stack_name" == "monitoring" ] && [ -f "$MONITORING_DIR/docker-compose.yml" ]; then
    compose_file="$MONITORING_DIR/docker-compose.yml"
  elif [ "$stack_name" == "dns" ] && [ -f "$DNS_DIR/docker-compose.yml" ]; then
    compose_file="$DNS_DIR/docker-compose.yml"
  else
    log_error "Docker Compose file not found for service '$stack_name' in any of the standard locations."
    return 1
  fi

  log_header "NUKE: Starting nuke for service: ${COLOR_YELLOW}$stack_name${COLOR_RESET}"

  read -p "Are you sure you want to nuke the service '$stack_name' and its volumes? (y/N): " -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log "Nuke of service '$stack_name' aborted."
    exit 0
  fi

  check_configs
  source "$PROJECT_ROOT/.env"
  source "$PROJECT_ROOT/scripts/machines.sh"

  # --- Nuke Service Stack ---
  log "Removing stack: ${COLOR_YELLOW}$stack_name${COLOR_RESET}"
  docker stack rm "$stack_name" || true
  log "Waiting for stack to be removed..."
  sleep 10

  # --- Remove Service Volumes ---
  _remove_service_volumes "$stack_name"

  log_success "Nuke of service '${COLOR_YELLOW}$stack_name${COLOR_RESET}' completed successfully."
}


redeploy_single_service() {
  local stack_name="$1"
  local compose_file=""

  # Find the compose file for the given stack
  if [ -f "$APPS_DIR/$stack_name/docker-compose.yml" ]; then
    compose_file="$APPS_DIR/$stack_name/docker-compose.yml"
  elif [ "$stack_name" == "reverse-proxy" ] && [ -f "$REVERSE_PROXY_DIR/docker-compose.yml" ]; then
    compose_file="$REVERSE_PROXY_DIR/docker-compose.yml"
  elif [ "$stack_name" == "monitoring" ] && [ -f "$MONITORING_DIR/docker-compose.yml" ]; then
    compose_file="$MONITORING_DIR/docker-compose.yml"
  elif [ "$stack_name" == "dns" ] && [ -f "$DNS_DIR/docker-compose.yml" ]; then
    compose_file="$DNS_DIR/docker-compose.yml"
  else
    log_error "Docker Compose file not found for stack '$stack_name' in any of the standard locations."
    return 1
  fi

  log_header "REDEPLOY: Starting redeployment for stack: ${COLOR_YELLOW}$stack_name${COLOR_RESET}"

  check_configs
  source "$PROJECT_ROOT/.env"
  source "$PROJECT_ROOT/scripts/machines.sh"

  # --- Nuke Service Stack ---
  log "Removing stack: ${COLOR_YELLOW}$stack_name${COLOR_RESET}"
  docker stack rm "$stack_name" || true
  log "Waiting for stack to be removed..."
  sleep 10

  # --- Remove Service Volumes ---
  _remove_service_volumes "$stack_name"

  # --- Redeploy Service Stack ---
  log_header "REDEPLOY: Deploying stack: ${COLOR_YELLOW}$stack_name${COLOR_RESET}"
  if deploy_stack "$stack_name" "$compose_file"; then
    log_success "Redeployment of stack '${COLOR_YELLOW}$stack_name${COLOR_RESET}' completed successfully."
  else
    log_error "Redeployment of stack '${COLOR_YELLOW}$stack_name${COLOR_RESET}' failed."
    return 1
  fi
}


# --- DEPLOY Functionality ---

deploy_stack() {
  local name="$1"
  local compose_file="$2"
  local max_retries=5
  local retry_delay=10 # in seconds
  local attempt=0
  local output

  log "Deploying stack: ${COLOR_YELLOW}$name${COLOR_RESET}"

  while (( attempt < max_retries )); do
    attempt=$((attempt + 1))

    # Step 1: Validate compose file first
    log "Validating compose file for stack '$name'..."
    local config_output
    if ! config_output=$(cd "$PROJECT_ROOT" && set -a && source .env && set +a && docker stack config -c "$compose_file" 2>&1); then
      log_error "Compose file validation failed for stack '$name':"
      echo "$config_output" | head -5 | while IFS= read -r line; do
        echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
      done
      if (( attempt < max_retries )); then
        log_warn "Retrying validation in $retry_delay seconds... (Attempt ${attempt}/${max_retries})"
        sleep "$retry_delay"
        continue
      else
        return 1
      fi
    fi

    # Step 2: Deploy with better error handling
    log "Deploying validated configuration for stack '$name'..."
    local deploy_exit_code
    output=$(cd "$PROJECT_ROOT" && set -a && source .env && set +a && echo "$config_output" | timeout 120s docker stack deploy --detach=false -c - "$name" 2>&1)
    deploy_exit_code=$?

    # Step 3: Check deployment result more carefully
    if [ $deploy_exit_code -eq 0 ]; then
      # Double-check that stack actually exists and has services
      sleep 3 # Give Docker a moment to register the stack
      local stack_exists service_count
      stack_exists=$(docker stack ls --format "{{.Name}}" | grep -c "^${name}$" || true)
      service_count=$(docker stack services "$name" 2>/dev/null | wc -l || echo "0")

      if [ "$stack_exists" -eq 1 ] && [ "$service_count" -gt 0 ]; then
        log_success "Stack '${COLOR_YELLOW}$name${COLOR_RESET}' deployed successfully."

        log "Displaying service placement..."
        sleep 2 # Give swarm a moment to update
        docker stack ps "$name" --filter "desired-state=running" --format "{{.Name}} → {{.Node}}" 2>/dev/null | while read -r placement; do
          echo -e "${COLOR_YELLOW}$placement${COLOR_RESET}"
        done

        return 0
      else
        log_warn "Deployment command succeeded but stack validation failed (stack_exists=$stack_exists, services=$service_count)"
      fi
    else
      log_warn "Deployment command failed with exit code $deploy_exit_code"
    fi

    # If we are here, the command failed.
    if (( attempt < max_retries )); then
      log_warn "Deployment of '${COLOR_YELLOW}$name${COLOR_RESET}' failed. Retrying in $retry_delay seconds... (Attempt ${attempt}/${max_retries})"
    else
      log_error "Failed to deploy stack '${COLOR_YELLOW}$name${COLOR_RESET}' after $max_retries attempts."
    fi

    # Show meaningful service errors grouped by type (only if stack exists)
    if docker stack ls --format "{{.Name}}" | grep -q "^${name}$"; then
        log_error "Service task errors for stack '$name':"
        sleep 2

        # Show unique meaningful errors (exclude generic exit codes)
        local meaningful_errors
        meaningful_errors=$(docker stack ps "$name" --no-trunc --filter "desired-state=shutdown" --format "{{.Name}}: {{.Error}}" 2>/dev/null | \
        grep -v "task: non-zero exit" | \
        grep -v "^[^:]*:[[:space:]]*$" | \
        sort -u | \
        head -10)

        if [[ -n "$meaningful_errors" ]]; then
            echo "$meaningful_errors" | while IFS= read -r line; do
                echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
            done
        else
            log_error "No specific error details available (stack may be initializing)"
        fi

        # Show error summary counts
        local error_summary
        error_summary=$(docker stack ps "$name" --filter "desired-state=shutdown" --format "{{.Error}}" 2>/dev/null | \
        sort | uniq -c | sort -nr | head -5)

        if [[ -n "$error_summary" ]]; then
            log_error "Error summary (top issues):"
            echo "$error_summary" | while IFS= read -r line; do
                echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
            done
        fi
    else
        log_error "Stack '$name' not found - may be initializing or deployment command failed"
    fi

    # Show deployment command output for debugging
    log_error "Deployment output analysis:"
    if [[ -n "$output" ]]; then
        # Show last few lines of output for context
        echo "$output" | tail -10 | while IFS= read -r line; do
            echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
        done

        # Show specific deployment failures
        local deploy_failures
        deploy_failures=$(echo "$output" | \
        grep -i "failed\|error\|invalid\|denied\|timeout" | \
        grep -v "overall progress:" | \
        grep -v "verify:" | \
        sort -u | \
        head -5)

        if [[ -n "$deploy_failures" ]]; then
            log_error "Specific deployment issues found:"
            echo "$deploy_failures" | while IFS= read -r line; do
                echo -e "${COLOR_RED}    $line${COLOR_RESET}" >&2
            done
        fi
    else
        log_error "No deployment output captured"
    fi

    # Additional debugging info
    log_error "Debugging info:"
    echo -e "${COLOR_RED}    - Exit code: $deploy_exit_code${COLOR_RESET}" >&2
    echo -e "${COLOR_RED}    - Timeout: 120s${COLOR_RESET}" >&2
    echo -e "${COLOR_RED}    - Attempt: ${attempt}/${max_retries}${COLOR_RESET}" >&2

    if (( attempt < max_retries )); then
        sleep "$retry_delay"
    fi
  done

  return 1
}



deploy_cluster() {
  local skip_apps=()
  local only_apps=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --help|-h)
        show_banner
        echo -e "${COLOR_BOLD}${COLOR_GREEN}USAGE:${COLOR_RESET} $0 deploy [options]"
        echo ""
        echo -e "${COLOR_BOLD}${COLOR_BLUE}OPTIONS:${COLOR_RESET}"
        echo -e "  ${COLOR_YELLOW}--skip-apps <apps>${COLOR_RESET}    Comma-separated list of apps to skip"
        echo -e "  ${COLOR_YELLOW}--only-apps <apps>${COLOR_RESET}    Comma-separated list of apps to deploy (only these)"
        echo -e "  ${COLOR_YELLOW}--help, -h${COLOR_RESET}           Show this help message"
        echo ""
        echo -e "${COLOR_BOLD}${COLOR_BLUE}EXAMPLES:${COLOR_RESET}"
        echo -e "  ${COLOR_GREEN}$0 deploy${COLOR_RESET}                          # Deploy all apps"
        echo -e "  ${COLOR_GREEN}$0 deploy --skip-apps homeassistant,emby${COLOR_RESET}    # Skip specific apps"
        echo -e "  ${COLOR_GREEN}$0 deploy --only-apps sonarr,radarr${COLOR_RESET}         # Deploy only specific apps"
        exit 0
        ;;
      --skip-apps)
        IFS=',' read -r -a skip_apps <<< "$2"
        shift 2
        ;;
      --only-apps)
        IFS=',' read -r -a only_apps <<< "$2"
        shift 2
        ;;
      *)
        log_error "Unknown option for deploy command: $1"
        echo "Use --help for usage information"
        exit 1
        ;;
    esac
  done

  check_configs
  source "$PROJECT_ROOT/.env"
  source "$PROJECT_ROOT/scripts/machines.sh"

  log_header "PHASE 1: MACHINE & SWARM SETUP"
  log "Setting up SSH for all machines..."
  machines_setup_ssh
  log "Checking for cifs-utils on all nodes..."
  machines_check_cifs_utils
  "$PROJECT_ROOT/scripts/swarm_cluster_manager.sh" init-cluster -c "$MACHINES_FILE"

  log_header "PHASE 2: CORE INFRASTRUCTURE"
  log "Ensuring overlay network '${COLOR_YELLOW}${NETWORK_NAME}${COLOR_RESET}' exists..."
  if ! docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    log "Network not found. Creating..."
    docker network create --driver=overlay --attachable "${NETWORK_NAME}"
    log_success "Network '${COLOR_YELLOW}${NETWORK_NAME}${COLOR_RESET}' created."
  else
    log "Network '${COLOR_YELLOW}${NETWORK_NAME}${COLOR_RESET}' already exists."
  fi

  # Deploy DNS stack first to ensure all services have DNS records
  if [ -f "$DNS_DIR/docker-compose.yml" ]; then
    deploy_stack "dns" "$DNS_DIR/docker-compose.yml"
    # Wait for DNS server to be ready, then configure DNS records
    log "Configuring DNS records for local services..."
    sleep 10  # Give DNS server time to start
    if [ -f "$PROJECT_ROOT/scripts/configure_dns_records.sh" ]; then
      "$PROJECT_ROOT/scripts/configure_dns_records.sh" --auto || log_warn "DNS records configuration failed, but deployment continues"
    fi
  else
    log_warn "DNS stack not found, skipping."
  fi

  deploy_stack "reverse-proxy" "$REVERSE_PROXY_DIR/docker-compose.yml"

  if [ -f "$MONITORING_DIR/docker-compose.yml" ]; then
    deploy_stack "monitoring" "$MONITORING_DIR/docker-compose.yml"
  else
    log_warn "Monitoring stack not found, skipping."
  fi

  log_header "PHASE 3: APPLICATION DEPLOYMENT"
  local pids=()
  for app_path in "$APPS_DIR"/*; do
    if [ -d "$app_path" ] && [ -f "$app_path/docker-compose.yml" ]; then
      local stack_name
      stack_name="$(basename "$app_path")"

      if [ ${#only_apps[@]} -gt 0 ] && [[ ! " ${only_apps[*]} " =~  ${stack_name}  ]]; then
        continue
      fi
      if [[ " ${skip_apps[*]} " =~  ${stack_name}  ]]; then
        log_warn "Skipping app stack as requested: $stack_name"
        continue
      fi

      deploy_stack "$stack_name" "$app_path/docker-compose.yml" &
      pids+=($!)
    fi
  done

  log "Waiting for all app deployments to complete..."
  local deployment_failed_count=0
  local deployed_stacks=()

  # Wait for all deployment processes
  for i in "${!pids[@]}"; do
    if ! wait "${pids[$i]}"; then
      deployment_failed_count=$((deployment_failed_count + 1))
    fi
  done

  # Collect all deployed stack names for verification
  for app_path in "$APPS_DIR"/*; do
    if [ -d "$app_path" ] && [ -f "$app_path/docker-compose.yml" ]; then
      local stack_name
      stack_name="$(basename "$app_path")"

      if [ ${#only_apps[@]} -gt 0 ] && [[ ! " ${only_apps[*]} " =~  ${stack_name}  ]]; then
        continue
      fi
      if [[ " ${skip_apps[*]} " =~  ${stack_name}  ]]; then
        continue
      fi

      deployed_stacks+=("$stack_name")
    fi
  done

  # Verify final service state regardless of deployment process results
  log "Verifying final service states..."
  local final_failed_count=0
  for stack_name in "${deployed_stacks[@]}"; do
    local total_services
    total_services=$(docker stack services "$stack_name" --format "{{.Replicas}}" 2>/dev/null | wc -l)

    if [ "$total_services" -eq 0 ]; then
      log_error "Stack '$stack_name' has no services running"
      final_failed_count=$((final_failed_count + 1))
    else
      # Check if all services have desired replicas running
      local all_healthy=true
      while IFS= read -r replica_info; do
        if [[ "$replica_info" == *"0/"* ]]; then
          all_healthy=false
          break
        fi
      done < <(docker stack services "$stack_name" --format "{{.Name}}: {{.Replicas}}" 2>/dev/null)

      if [ "$all_healthy" = true ]; then
        log_success "Stack '$stack_name' is healthy"
      else
        log_error "Stack '$stack_name' has unhealthy services"
        final_failed_count=$((final_failed_count + 1))
      fi
    fi
  done

  # Report final results based on actual service state
  if [ "$final_failed_count" -gt 0 ]; then
    log_error "$final_failed_count stack(s) are not running properly. Please review service logs."
    if [ "$deployment_failed_count" -gt 0 ]; then
      log_error "Note: $deployment_failed_count deployment process(es) also failed during initial deployment."
    fi
  else
    log_success "All application stacks are running successfully."
    if [ "$deployment_failed_count" -gt 0 ]; then
      log_warn "Note: $deployment_failed_count deployment process(es) failed initially but services recovered successfully."
    fi
  fi

  log_header "PHASE 4: CLUSTER MONITORING"
  log "Running cluster status monitor..."
  "$PROJECT_ROOT/scripts/swarm_cluster_manager.sh" monitor-cluster

  log_header "DEPLOYMENT COMPLETE"
  log_success "All stacks deployed!"
}

# --- Main Entrypoint ---

main() {
  # Always show banner for any command
  show_compact_banner
  echo

  check_dependencies

  local command="deploy"
  local args=("$@")

  # Check if the first argument is a known command
  if [[ "${1:-}" == "deploy" || "${1:-}" == "nuke" || "${1:-}" == "redeploy-service" ]]; then
    command="$1"
    args=("${@:2}")
  # If the first arg is not a known command, but looks like an option, assume 'deploy'
  elif [[ "${1:-}" == -* ]]; then
    command="deploy"
    args=("$@")
  # If the first arg is not a command and not an option, and not empty, it's an error
  elif [[ -n "${1:-}" ]]; then
      log_error "Unknown command: '$1'"
      echo ""
      echo -e "${COLOR_BOLD}${COLOR_BLUE}Available commands:${COLOR_RESET}"
      echo -e "  ${COLOR_GREEN}deploy${COLOR_RESET}           Full homelab deployment (default)"
      echo -e "  ${COLOR_RED}nuke${COLOR_RESET}             Complete infrastructure cleanup"
      echo -e "  ${COLOR_YELLOW}redeploy-service${COLOR_RESET} Redeploy a specific service"
      echo ""
      echo -e "${COLOR_BOLD}${COLOR_BLUE}Usage:${COLOR_RESET}"
      echo -e "  ${COLOR_GREEN}$0 [deploy|nuke|redeploy-service] [options...]${COLOR_RESET}"
      echo -e "  ${COLOR_GREEN}$0 deploy --help${COLOR_RESET} for deployment options"
      exit 1
  fi

  case "$command" in
    deploy)
      deploy_cluster "${args[@]}"
      ;;
    nuke)
      if [ -n "${args[0]:-}" ]; then
        nuke_single_service "${args[0]}"
      else
        nuke_cluster
      fi
      ;;
    redeploy-service)
      if [ -z "${args[0]:-}" ]; then
        log_error "Usage: $0 redeploy-service <service_name>"
        exit 1
      fi
      redeploy_single_service "${args[0]}"
      ;;
  esac
}

if [ "${BASH_SOURCE[0]}" -ef "$0" ]; then
    main "$@"
fi
